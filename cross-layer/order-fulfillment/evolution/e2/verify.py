#!/usr/bin/env python3
"""Qualify G2 at the shared HTTP boundary and read-only physical facts."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from build import CASE, ROOT, load, build_tools
from cancellation_checks import Checks, BehavioralFailure
import visible_checks

base = load('baseline_http_checks', CASE/'conditions/conventional/tests/contract_tests.py')
Client=base.Client

def run(*args): return subprocess.check_output(args,text=True).strip()


def free_port():
    import socket
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


def observe(container, condition):
    order,inventory,reservation,identity=('orders','inventory','reservations','id') if condition=='conventional' else ('cohesive_orders','cohesive_inventory','cohesive_reservations','reservation_id')
    sql=f'''SELECT json_build_object(
      'orders',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT order_id AS id,status FROM {order} WHERE order_id LIKE 'e2-%') x),
      'inventory',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT sku,available,max_per_order AS "maxPerOrder" FROM {inventory} WHERE sku LIKE 'e2-%') x),
      'reservations',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT {identity} AS id,order_id AS "orderId",sku,quantity FROM {reservation} WHERE order_id LIKE 'e2-%') x));'''
    if condition=='conventional': sql=sql.replace(f'SELECT order_id AS id,status FROM {order} WHERE order_id',f'SELECT id,status FROM {order} WHERE id')
    return json.loads(run('docker','exec',container,'psql','-U','postgres','-d',condition,'-At','-c',sql))


def start(executable, folder, env, log):
    url=f'http://127.0.0.1:{free_port()}'
    process=subprocess.Popen(['dotnet',str(executable),'--urls',url],cwd=folder,env=env,stdout=log,stderr=log)
    try:
        for _ in range(150):
            if process.poll() is not None: raise RuntimeError('Host exited during startup')
            try:
                urllib.request.urlopen(url+'/orders/e2-0',timeout=1).close();return process,url
            except (urllib.error.URLError,TimeoutError):time.sleep(.1)
        raise RuntimeError('Host readiness deadline')
    except BaseException:
        stop(process);raise


def stop(process):
    process.terminate()
    try:process.wait(timeout=20)
    except subprocess.TimeoutExpired:process.kill();process.wait()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--condition',choices=['conventional','cohesive'])
    parser.add_argument('--e2-only',action='store_true')
    args=parser.parse_args();args.output=args.output.resolve();args.output.mkdir(parents=True,exist_ok=False)
    args.fixtures=args.fixtures.resolve()
    if not args.condition:
        for relative in ['Program.cs','Contracts.cs','QuantityLimitInput.cs','OperationQueue.cs','ReadResults.cs']:
            a,b=(args.fixtures/c/'src/Fulfillment.Application'/relative for c in ['conventional','cohesive'])
            assert a.read_bytes()==b.read_bytes(),('shared source differs',relative)
        for relative in ['CONTRACT.md','schemas.json','seed.schema.json','contract-examples.json','tests/e1_checks.py','tests/e2_checks.py']:
            assert (args.fixtures/'conventional'/relative).read_bytes()==(args.fixtures/'cohesive'/relative).read_bytes(),relative
    name='e2-'+uuid.uuid4().hex[:12];image='postgres:17.10-alpine3.24';started=False
    records={};condition=None
    try:
        if not args.e2_only:
            command = [sys.executable, '-B', str(ROOT.parent/'e1/verify.py'),
                       '--fixtures', str(args.fixtures), '--output', str(args.output/'prior')]
            if args.condition:
                command += ['--condition', args.condition]
            with (args.output/'prior.log').open('w') as log:
                subprocess.run(command, stdout=log, stderr=log, check=True, timeout=600)
        image_id=run('docker','image','inspect',image,'--format','{{.Id}}')
        run('docker','run','-d','--name',name,'-e','POSTGRES_PASSWORD=fixture-only','-p','127.0.0.1::5432',image);started=True
        for _ in range(100):
            if subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
            time.sleep(.1)
        else:raise RuntimeError('PostgreSQL readiness deadline')
        port=run('docker','port',name,'5432/tcp').rsplit(':',1)[1]
        for condition in ([args.condition] if args.condition else ['conventional','cohesive']):
            folder=args.fixtures/condition;fingerprint=build_tools.verify_build(folder)
            output=args.output/condition;output.mkdir()
            run('docker','exec',name,'psql','-U','postgres','-c',f'CREATE DATABASE {condition}')
            from cancellation_checks import fixture
            data=fixture()
            for k in data:
                data[k]+=visible_checks.SEED[k]

            seed=output/'seed.json';seed.write_text(json.dumps(data))
            executable=folder/'src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll'
            env=dict(os.environ,ConnectionStrings__Orders=f'Host=127.0.0.1;Port={port};Database={condition};Username=postgres;Password=fixture-only;Timeout=10',ASPNETCORE_ENVIRONMENT='Production')
            with (output/'host.log').open('w') as log:
                subprocess.run(['dotnet',str(executable),'--seed',str(seed)],cwd=folder,env=dict(env,FULFILLMENT_SETUP='1'),stdout=log,stderr=log,check=True,timeout=90)
                process,url=start(executable,folder,env,log)
                try:
                    visible=visible_checks.exercise(Client,url) if not args.e2_only else []
                    checker=Checks(Client,url,lambda:observe(name,condition),output)
                    result=checker.run()
                finally:stop(process)
                process,url=start(executable,folder,env,log)
                try:
                    checker.c=Client(url);checker.after_restart()
                    result["commands"]=len(checker.trace)
                    result["cleanRestartVerified"]=True
                finally:stop(process)
                assert build_tools.verify_build(folder)==fingerprint,'Build changed during execution'
            records[condition]={'visibleE2':visible,'e2':result,'buildManifestSha256':fingerprint}
        if not args.condition:
            a,b=(records[c] for c in ['conventional','cohesive'])
            for k in ['visibleE2','e2']:assert a[k]==b[k],('condition equivalence',k)
        report={'passed':True,'priorCheckpointsVerified':not args.e2_only,'postgresImage':image,'postgresImageId':image_id,'conditions':records}
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print('E2 verification passed:',', '.join(records),flush=True)
    except BehavioralFailure as error:
        (args.output/'failure.json').write_text(json.dumps({'kind':'behavioral','condition':condition,'obligation':error.obligation,'assertion':error.assertion,'detail':str(error)},indent=2)+'\n')
        raise
    except Exception as error:
        (args.output/'failure.json').write_text(json.dumps({'kind':'unqualified','condition':condition,'detail':str(error)},indent=2)+'\n')
        raise
    finally:
        if started:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,check=True)


if __name__=='__main__':main()
