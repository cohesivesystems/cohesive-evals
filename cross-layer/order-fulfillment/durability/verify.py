#!/usr/bin/env python3
"""External worker-kill tests against isolated durable reference solutions."""
import argparse
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent
CASE=ROOT.parent
sys.path.insert(0,str(CASE/'verification'))
from verify import run, free_port, IMAGE
from build import reference_fingerprint, verify_build
spec=importlib.util.spec_from_file_location('contract_tests',CASE/'conditions/conventional/tests/contract_tests.py')
suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)
POINTS=['none','before-admission-commit','after-admission-commit','before-dispatch','after-reserve','after-submit','after-reservation','after-release','before-result-commit','terminal-failure']


def wait_until(test, seconds, label):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if test():return
        time.sleep(.1)
    raise AssertionError('Deadline exceeded: '+label)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition',choices=['conventional','cohesive'])
    parser.add_argument('--point',choices=POINTS)
    parser.add_argument('--reject',action='store_true')
    parser.add_argument('--references',type=Path,default=CASE/'artifacts/durable-reference')
    parser.add_argument('--output',type=Path,default=CASE/'artifacts/durability')
    args=parser.parse_args()
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    (output/'assertion-failure.json').unlink(missing_ok=True)
    (output/'report.json').unlink(missing_ok=True)
    manifest=json.loads((ROOT/'dependency-manifest.json').read_text())
    suffix=uuid.uuid4().hex[:10];pg='order-recovery-pg-'+suffix;dts='order-recovery-dts-'+suffix
    owned=[];process=None;records=[]
    build_manifests={c:verify_build(args.references.resolve()/c) for c in ([args.condition] if args.condition else ['conventional','cohesive'])}
    try:
        run('docker','run','-d','--name',pg,'-e','POSTGRES_PASSWORD=fixture-only','-p','127.0.0.1::5432',IMAGE);owned.append(pg)
        run('docker','run','-d','--name',dts,'-p','127.0.0.1::8080',manifest['schedulerImage']);owned.append(dts)
        wait_until(lambda:subprocess.run(['docker','exec',pg,'pg_isready','-h','127.0.0.1','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0,30,'PostgreSQL ready')
        dbport=run('docker','port',pg,'5432/tcp').rsplit(':',1)[1]
        dtsport=run('docker','port',dts,'8080/tcp').rsplit(':',1)[1]
        def scheduler_ready():
            try:
                with socket.create_connection(('127.0.0.1',int(dtsport)),timeout=.5): return True
            except OSError:return False
        wait_until(scheduler_ready,30,'scheduler ready')
        for condition in ([args.condition] if args.condition else ['conventional','cohesive']):
            folder=args.references.resolve()/condition
            executable=folder/'src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll'
            for index, point in enumerate([args.point] if args.point else POINTS):
                database=f'{condition}_{index}'
                run('docker','exec',pg,'psql','-U','postgres','-c',f'CREATE DATABASE {database}')
                evidence=output/condition/point;evidence.mkdir(parents=True,exist_ok=True)
                marker=evidence/'barrier';marker.unlink(missing_ok=True)
                terminal=point=='terminal-failure'
                rejecting=args.reject or point=='after-release'
                seed={'orders':[{'id':o,'status':'Submitted' if o=='a' and rejecting else 'Draft'} for o in ['a','b','c','untouched']],
                      'inventory':[{'sku':'stock','available':5},{'sku':'untouched','available':9}], 'reservations':[]}
                seed_path=evidence/'seed.json';seed_path.write_text(json.dumps(seed))
                env=dict(os.environ,ConnectionStrings__Orders=f'Host=127.0.0.1;Port={dbport};Database={database};Username=postgres;Password=fixture-only',
                         DURABLE_TASK_CONNECTION=f'Endpoint=http://127.0.0.1:{dtsport};TaskHub=default;Authentication=None', ASPNETCORE_ENVIRONMENT='Production')
                with (evidence/'host.log').open('w') as log:
                    subprocess.run(['dotnet',str(executable),'--seed',str(seed_path)],cwd=folder,env=dict(env,FULFILLMENT_SETUP='1'),stdout=log,stderr=log,check=True,timeout=60)
                    port=free_port();url=f'http://127.0.0.1:{port}';client=suite.Client(url)
                    def start(crash):
                        nonlocal process
                        current=dict(env)
                        if crash:
                            if terminal: current.update(EVAL_FAIL_POINT="before-reserve",EVAL_FAIL_MARKER=str(marker))
                            else: current.update(EVAL_CRASH_POINT=point,EVAL_CRASH_MARKER=str(marker))
                        process=subprocess.Popen(['dotnet',str(executable),'--urls',url],cwd=folder,env=current,stdout=log,stderr=log)
                        def ready():
                            if process.poll() is not None:raise RuntimeError('Host exited; see '+str(evidence/'host.log'))
                            try:return client.request('GET','/orders/a')[0]==200
                            except (urllib.error.URLError,ConnectionError):return False
                        wait_until(ready,30,'host ready')
                    start(point!='none')
                    request={'requestId':'request-a','orderId':'a','sku':'stock','quantity':3}
                    receipt=None
                    if point in ['before-admission-commit','after-admission-commit']:
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            pending=pool.submit(client.request,'POST','/fulfillment',request)
                            wait_until(marker.exists,30,point)
                            process.kill();process.wait(timeout=10);process=None
                            try: pending.result(timeout=5)
                            except (OSError,TimeoutError):pass
                    else:
                        status,receipt=client.request('POST','/fulfillment',request);assert status==202,(status,receipt)
                        if point not in ['none','terminal-failure']:
                            wait_until(marker.exists,60,point)
                            process.kill();process.wait(timeout=10);process=None
                    if point not in ['none','terminal-failure']:start(False)
                    # Ambiguous unacknowledged admission may require retry. An acknowledged
                    # admission must recover autonomously through its original result URL.
                    if receipt is None:
                        status,receipt=client.request('POST','/fulfillment',request);assert status==202
                    outcome='OrderRejected' if rejecting else 'ReservedAndSubmitted'
                    expected={'code':'ExecutionFailed'} if terminal else {'status':'Rejected' if rejecting else 'Submitted','outcome':outcome}
                    expected_status=500 if terminal else 200
                    final=None
                    def completed():
                        nonlocal final
                        final=client.request('GET',receipt['resultUrl'])
                        assert final[0] in [200,202,500],('original result lookup',final)
                        return final[0]!=202
                    wait_until(completed,120,'recovery completion')
                    assert final==(expected_status,expected),('completion after recovery',final)
                    assert client.request('POST','/fulfillment',request)==(202,receipt)
                    assert client.request('POST','/fulfillment',{**request,'quantity':4})==(409,{'code':'RequestIdentityConflict'})
                    assert client.request('GET','/inventory/stock')==(200,{'sku':'stock','available':5 if rejecting or terminal else 2}), 'stock after recovery'
                    details=client.request('GET','/orders/a/details');assert details[0]==200
                    assert len(details[1]['reservations'])==(0 if rejecting or terminal else 1), 'reservation cardinality'
                    if not rejecting:
                        client.fulfill('request-b','b','stock',5 if terminal else 2,'ReservedAndSubmitted')
                        client.fulfill('request-c','c','stock',1,'InsufficientStock')
                        assert client.request('GET','/inventory/stock')==(200,{'sku':'stock','available':0})
                    # Physical duplicate rows cannot be hidden by public projections.
                    table='reservations' if condition=='conventional' else 'cohesive_reservations'
                    physical=json.loads(run('docker','exec',pg,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','postgres','-d',database,'-c',f"BEGIN READ ONLY; SELECT json_build_object('count',count(*),'quantity',coalesce(sum(quantity),0)) FROM {table}; COMMIT;"))
                    assert physical==({'count':0,'quantity':0} if rejecting else {'count':1 if terminal else 2,'quantity':5}),physical
                    assert client.request('GET','/inventory/untouched')==(200,{'sku':'untouched','available':9})
                    assert client.request('GET','/orders/untouched')==(200,{'id':'untouched','status':'Draft'})
                    # Completed result survives another restart too.
                    process.kill();process.wait(timeout=10);process=None;start(False)
                    assert client.request('POST','/fulfillment',request)==(202,receipt)
                    assert client.request('GET',receipt['resultUrl'])==(expected_status,expected)
                    process.kill();process.wait(timeout=10);process=None
                    record={'condition':condition,'point':point,'passed':True,'completion':expected,'physical':physical}
                    records.append(record);(evidence/'result.json').write_text(json.dumps(record,indent=2)+'\n')
                    print(condition,point,'passed',flush=True)
        assert build_manifests=={c:verify_build(args.references.resolve()/c) for c in build_manifests}, 'Build changed during verification'
        (output/'report.json').write_text(json.dumps({'passed':True,'cases':records,'schedulerImage':manifest['schedulerImage'],
            'buildManifests':build_manifests,
            'referenceFingerprints':{c:reference_fingerprint(args.references.resolve()/c) for c in ([args.condition] if args.condition else ['conventional','cohesive'])},
            'limitations':['Worker/API crashes only; scheduler and databases remain available','Single active host; sequential independent intents','Reference qualification, not scored agent evidence']},indent=2)+'\n')
    except AssertionError as error:
        (output/'assertion-failure.json').write_text(json.dumps({'error':str(error),'condition':condition,'point':point},indent=2)+'\n')
        raise
    finally:
        if process is not None:process.kill();process.wait(timeout=10)
        for container in reversed(owned):subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,check=True)

if __name__=='__main__':main()
