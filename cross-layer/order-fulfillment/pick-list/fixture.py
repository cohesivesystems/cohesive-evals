"""Disposable capped G0 hosts and PostgreSQL seeding for the paired pick-list runs."""
from contextlib import contextmanager
import json
import time
from uuid import uuid4

from cohesive_evals.postgres import IMAGE as PG
from cohesive_evals.errors import AdapterError
from cohesive_evals.runtime import capture
from workload import fixture

NET = 'mcr.microsoft.com/dotnet/aspnet:10.0'


def docker(*args):
    """Run a bounded Docker command and return stdout or an infrastructure failure."""
    return capture('docker', *args)


def port(container, internal):
    """Find the host-assigned loopback port of an already running container."""
    return int(docker('port', container, internal).rsplit(':', 1)[1])


@contextmanager
def hosts(published, out):
    """Start isolated capped containers and preserve logs plus deployment metadata on exit."""
    name = 'pick-' + uuid4().hex[:10]
    pg, app = name + '-pg', name + '-app'
    docker('network', 'create', name)
    created = []
    try:
        docker('run', '-d', '--name', pg, '--network', name, '--network-alias', 'db',
               '--cpus', '2', '--memory', '4g', '--memory-swap', '4g', '-p', '127.0.0.1::5432',
               '-e', 'POSTGRES_DB=orders', '-e', 'POSTGRES_PASSWORD=fixture', PG)
        created.append(pg)
        for _ in range(120):
            try:
                if 'accepting connections' in docker('exec', pg, 'pg_isready', '-h', '127.0.0.1'):
                    break
            except AdapterError:
                pass
            time.sleep(.25)
        else:
            raise RuntimeError('PostgreSQL readiness deadline')
        docker('run', '-d', '--name', app, '--network', name, '--cpus', '2', '--memory', '2g',
               '--memory-swap', '2g', '-p', '127.0.0.1::8080', '-v', f'{published}:/app:ro',
               '-e', 'Logging__LogLevel__Default=Warning', '-e',
               'ConnectionStrings__Orders=Host=db;Database=orders;Username=postgres;Password=fixture',
               NET, 'dotnet', '/app/Fulfillment.Application.dll')
        created.append(app)
        info = {c: docker('inspect', '-f', '{{.Image}} {{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}', c)
                for c in created}
        (out / 'environment.json').write_text(json.dumps(dict(containers=info,
            docker=docker('info', '-f', '{{.OperatingSystem}} {{.KernelVersion}} {{.Architecture}} {{.Driver}}')), indent=2))
        yield pg, app, f'postgres://postgres:fixture@127.0.0.1:{port(pg,"5432")}/orders', port(app,'8080')
    finally:
        for container in reversed(created):
            (out / (container.split('-')[-1] + '.log')).write_text(docker('logs', '--tail', '80', container))
            docker('rm', '-fv', container)
        docker('network', 'rm', name)


async def seed(db, arm, total):
    """Write the same source facts using each G0 schema, including all historical orders."""
    orders, stock = fixture()
    native = arm == 'cohesive'
    prefix = 'cohesive_' if native else ''
    order_id = 'order_id' if native else 'id'
    extra = ', partition_key, observation_version' if native else ''
    values = ", 'local', 0" if native else ''
    async with db.transaction():
        await db.execute(f"""INSERT INTO {prefix}orders ({order_id},status,location,priority,warehouse_status,held{extra})
            SELECT 'H'||lpad(n::text,7,'0'),'Submitted','L00',0,'Shipped',false{values}
            FROM generate_series(1,$1::integer) n""", total-len(orders))
        # G0 knows Draft/Submitted. Warehouse packed eligibility is the additive fact.
        suffix = ('local', 0) if native else ()
        extra_cols = ('partition_key','observation_version') if native else ()
        await db.copy_records_to_table(prefix+'orders', columns=(order_id,'status','location','priority','warehouse_status','held')+extra_cols,
            records=[(o.id,'Submitted',o.location,o.priority,'Packed' if o.packed else 'Pending',o.held)+suffix for o in orders.values()])
        skus = sorted({sku for o in orders.values() for sku,_ in o.lines})
        await db.copy_records_to_table(prefix+'inventory', columns=('sku','available')+extra_cols,
            records=[(sku,0)+suffix for sku in skus])
        await db.copy_records_to_table(prefix+'reservations',
            columns=(('reservation_id' if native else 'id'),'order_id','sku','quantity')+extra_cols,
            records=[(f'{o.id}-{i}',o.id,sku,qty)+suffix for o in orders.values() for i,(sku,qty) in enumerate(o.lines)])
        await db.copy_records_to_table('pick_stock', columns=('location','sku','units'),
            records=[(loc,sku,n) for (loc,sku),n in stock.items()])
    await db.execute('ANALYZE')


async def mutate(db, change):
    """Commit exactly one source mutation and fail setup if the fixture row is absent."""
    loc, kind, key, val = change
    if kind == 'hold':
        status = await db.execute('UPDATE pick_orders SET held=$1 WHERE id=$2 AND location=$3',val,key,loc)
    else:
        status = await db.execute('UPDATE pick_stock SET units=$1 WHERE location=$2 AND sku=$3',val,loc,key)
    if status != 'UPDATE 1':
        raise ValueError(f'Unexpected mutation result {status}')


def resources(container):
    """Read cumulative CPU microseconds and anonymous resident bytes from cgroup v2."""
    def counters(file):
        """Parse cgroup key/value counters."""
        return dict(line.split() for line in docker('exec',container,'cat','/sys/fs/cgroup/'+file).splitlines())
    return dict(cpuUs=int(counters('cpu.stat')['usage_usec']), rssBytes=int(counters('memory.stat')['anon']))
