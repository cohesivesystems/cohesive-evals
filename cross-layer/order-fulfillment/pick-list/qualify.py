"""Drive fixed-rate independent readers, committed writes and visibility probes on fresh hosts."""
import argparse
import asyncio
import gzip
import json
from math import ceil, inf
from pathlib import Path
import platform
from time import monotonic
import traceback

import aiohttp
import asyncpg
from fixture import hosts, seed, mutate, resources, docker, port
from workload import digest, freeze, trace

ROOT = Path(__file__).resolve().parent
GOLD = json.loads((ROOT/'golden.json').read_text())
LOCATIONS = [f'L{i:02}' for i in range(32)]


def require(value, message):
    """Raise a behavioral failure with a specific observable mismatch."""
    if not value:
        raise AssertionError(message)


def percentile(values):
    """Nearest-rank p99, preserving deadline misses as infinite."""
    result = sorted(values)[ceil(.99*len(values))-1]
    return result if result != inf else 'infinite'


async def run_one(arm, size, build, out, smoke):
    """Run controls, warm-up and one measured repetition. Never reuse database state."""
    out.mkdir(parents=True)
    started = monotonic()
    with hosts(build/arm/'published', out) as (pg, app, dsn, http_port):
        db = await asyncpg.connect(dsn)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as client:
            async def get(loc):
                """Return exact wire-page hash; non-200 or malformed payload fails the read."""
                async with client.get(f'http://127.0.0.1:{http_port}/locations/{loc}/pick-list') as reply:
                    require(reply.status == 200, f'{loc} HTTP {reply.status}')
                    return digest(await reply.json())

            async def listening():
                """Wait for bound TCP listener without consuming the first application read."""
                nonlocal http_port
                http_port = port(app,'8080')
                deadline = monotonic()+30
                while monotonic() < deadline:
                    try:
                        _, writer = await asyncio.open_connection('127.0.0.1',http_port)
                        writer.close()
                        await writer.wait_closed()
                        # Docker can accept TCP before Kestrel; schema + process readiness via unknown route.
                        async with client.get(f'http://127.0.0.1:{http_port}/health-unmapped') as response:
                            if response.status == 404:
                                return
                    except (OSError, aiohttp.ClientError):
                        pass
                    await asyncio.sleep(.1)
                raise RuntimeError('host readiness deadline')

            await listening()
            first_ready = monotonic()-started
            seed_start = monotonic()
            await seed(db,arm,size)
            seed_seconds = monotonic()-seed_start
            population = await db.fetchrow("""select count(*) as total,
                count(*) filter (where warehouse_status='Shipped') as history from pick_orders""")
            require(population['total']==size and population['history']==size-3206,'seed population')
            for loc in [*LOCATIONS,'controls','unknown']:
                require(await get(loc)==GOLD['pages'][loc][0],f'populated-first-read {loc}')
            first = next(trace())
            docker('stop',app)
            await mutate(db,first)
            docker('start',app)
            await listening()
            require(await get(first[0])==GOLD['pages'][first[0]][1],'restart catch-up')
            await mutate(db,(first[0],'hold',first[2],False))
            sql = (ROOT/'candidate/pick-list.sql').read_text()
            plan = await db.fetchval('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+sql,'L00')
            (out/'plan.json').write_text(plan)
            (out/'postgres.json').write_text(json.dumps(dict(version=await db.fetchval('select version()'),
                extensions=[dict(r) for r in await db.fetch('select extname,extversion from pg_extension')],
                settings=[dict(r) for r in await db.fetch('select name,setting,unit from pg_settings order by name')]),indent=2))
            ready = monotonic()-started
            warm = 1 if smoke else 60
            warm_start = monotonic()
            async def warm_read(i):
                """Exercise the same read mix as foreground clients before measurement."""
                await asyncio.sleep(max(0,warm_start+i/32-monotonic()))
                loc = LOCATIONS[i%32]
                require(await get(loc)==GOLD['pages'][loc][0],f'warm page {loc}')
            await asyncio.gather(*(warm_read(i) for i in range(warm*32)))

            async def buffers():
                """Fetch cumulative database buffer counters on a fresh stats snapshot."""
                return await db.fetchrow('select blks_hit,blks_read from pg_stat_database where datname=current_database()')

            before = {c:resources(c) for c in (app,pg)}
            b0 = await buffers()
            duration = 13 if smoke else 600
            count = duration*10
            # Entries are [class, index, scheduled lag ms, latency ms, observed hash].
            raw, read_times, freshness, read_lag, write_lag, errors = [],[],[],[],[],[]
            states = {loc:[GOLD['pages'][loc][0]] for loc in LOCATIONS}
            epochs = dict.fromkeys(LOCATIONS,0)
            probes, foreground = [],[]
            start = monotonic()

            async def foreground_read(i):
                """Validate complete pages, allowing a commit concurrent with this read."""
                loc = LOCATIONS[i%32]
                sent = monotonic()
                prior = set(states[loc][-2:])
                observed = await get(loc)
                finished = monotonic()
                if observed not in prior.union(states[loc][-2:]):
                    errors.append(f'foreground {i} invalid page {observed}')
                lag = (sent-start-i/32)*1000
                latency = (finished-sent)*1000
                read_times.append(latency)
                read_lag.append(lag)
                raw.append(['read',i,lag,latency,observed])

            async def visibility(i,loc,wanted,ack,epoch):
                """Poll independently; a superseding acknowledgment censors the old sample as a miss."""
                attempt = 0
                while epochs[loc]==epoch and monotonic()-ack < 3.2:
                    await asyncio.sleep(max(0,ack+.1*attempt-monotonic()))
                    observed = await get(loc)
                    delay = (monotonic()-ack)*1000
                    raw.append(['probe',i,attempt,delay,observed])
                    if epochs[loc]==epoch and observed==wanted:
                        freshness.append(delay)
                        return
                    if observed not in states[loc][-3:]:
                        errors.append(f'probe {i} invalid page {observed}')
                    attempt += 1
                freshness.append(inf)

            async def reads():
                """Schedule reads on the original clock irrespective of response time."""
                for i in range(duration*32):
                    await asyncio.sleep(max(0,start+i/32-monotonic()))
                    foreground.append(asyncio.create_task(foreground_read(i)))
                await asyncio.gather(*foreground)

            async def writes():
                """Commit the frozen trace, recording acknowledgments and starting independent probes."""
                for i,change in enumerate(trace()):
                    if i==count:
                        break
                    await asyncio.sleep(max(0,start+i/10-monotonic()))
                    sent = monotonic()
                    loc = change[0]
                    wanted = GOLD['pages'][loc][i//32%4+1]
                    states[loc].append(wanted)
                    await mutate(db,change)
                    ack = monotonic()
                    lag = (sent-start-i/10)*1000
                    write_lag.append(lag)
                    raw.append(['write',i,lag,(ack-sent)*1000,wanted])
                    epochs[loc] += 1
                    probes.append(asyncio.create_task(visibility(i,loc,wanted,ack,epochs[loc])))
                last = ack
                while True:
                    results = await asyncio.gather(*(get(loc) for loc in LOCATIONS))
                    if results==[states[l][-1] for l in LOCATIONS]:
                        break
                    require(monotonic()-last < 2,'final exact pages within deadline')
                    await asyncio.sleep(.05)
                return monotonic()-last

            _, final_seconds = await asyncio.gather(reads(),writes())
            await asyncio.gather(*probes)
            elapsed = monotonic()-start
            after = {c:resources(c) for c in (app,pg)}
            # Give async PostgreSQL statistics the normal flush interval after load stops.
            await asyncio.sleep(1.1)
            b1 = await buffers()
            with gzip.open(out/'samples.jsonl.gz','wt') as stream:
                for record in raw:
                    stream.write(json.dumps(record,separators=(',',':'))+'\n')
            report = dict(arm=arm,orders=size,writes=count,reads=len(read_times),durationSeconds=elapsed,
                foregroundP99Ms=percentile(read_times),visibilityP99Ms=percentile(freshness),
                overTwoSeconds=sum(t>2000 for t in freshness),unseen=sum(t==inf for t in freshness),
                readLagP99Ms=percentile(read_lag),writeLagP99Ms=percentile(write_lag),
                maxReadLagMs=max(read_lag),maxWriteLagMs=max(write_lag),finalSeconds=final_seconds,
                cpuSeconds={k:(after[c]['cpuUs']-before[c]['cpuUs'])/1e6 for k,c in [('db',pg),('app',app)]},
                rssBytes={k:after[c]['rssBytes'] for k,c in [('db',pg),('app',app)]},
                bufferHitsPerWrite=(b1[0]-b0[0])/count,bufferReadsPerWrite=(b1[1]-b0[1])/count,
                firstReadySeconds=first_ready,setupThroughRestartSeconds=ready,seedSeconds=seed_seconds,host=platform.platform(),errors=errors)
            (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            require(not errors and report['reads']==duration*32 and len(freshness)==count and
                    percentile(read_times)<=250 and sorted(freshness)[ceil(.99*count)-1]<=2000 and
                    final_seconds<=2 and elapsed<=duration+2,'load acceptance')
        await db.close()


async def main(args):
    """Alternate conditions by repetition, persisting a classified failure if a run aborts."""
    require(freeze()==GOLD,'frozen oracle digest')
    for size in args.scales:
        for repetition in range(1,args.repetitions+1):
            arms = ('conventional','cohesive')
            if repetition%2==0:
                arms = arms[::-1]
            for arm in arms:
                out = args.output/f'{size}-{repetition}-{arm}'
                print(out.name,flush=True)
                try:
                    await run_one(arm,size,args.build,out,args.smoke)
                except Exception as error:
                    (out/'failure.json').write_text(json.dumps(dict(
                        category='behavior' if isinstance(error,AssertionError) else 'infrastructure',
                        error=str(error),traceback=traceback.format_exc()),indent=2))
                    raise


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--scales',type=int,nargs='+',default=[100000,1000000])
    parser.add_argument('--repetitions',type=int,default=3)
    parser.add_argument('--smoke',action='store_true')
    asyncio.run(main(parser.parse_args()))
