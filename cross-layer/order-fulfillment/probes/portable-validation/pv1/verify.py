#!/usr/bin/env python3
"""PV1 process-level checks against both transports and physical PostgreSQL facts."""
import argparse
import copy
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
import build
import checks
import visible_checks

sys.path.insert(0,str(build.CASE / 'evolution'))
import harness
base = harness.load('pv1_http_client',build.CASE / 'conditions/conventional/tests/contract_tests.py')

class World:
    def __init__(self, folder, output, container, port, condition, seed, batch=None, raw=False):
        self.output=output; output.mkdir(parents=True)
        self.container=container; self.condition=condition
        self.database='pv'+uuid.uuid4().hex[:12]
        harness.run('docker','exec',container,'psql','-U','postgres','-c',f'CREATE DATABASE {self.database}')
        self.env=dict(os.environ,ConnectionStrings__Orders=f'Host=127.0.0.1;Port={port};Database={self.database};Username=postgres;Password=fixture-only;Timeout=10',ASPNETCORE_ENVIRONMENT='Production')
        self.folder=folder
        self.ready_path="/orders/"+seed["orders"][0]["id"]
        self.executable=folder/'src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll'
        self.log=(output/'host.log').open('w')
        seedfile=output/'seed.json';seedfile.write_text(json.dumps(seed))
        subprocess.run(['dotnet',str(self.executable),'--seed',str(seedfile)],cwd=folder,env=dict(self.env,FULFILLMENT_SETUP='1'),stdout=self.log,stderr=self.log,check=True,timeout=90)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); http_port=sock.getsockname()[1]
        self.url=f'http://127.0.0.1:{http_port}'
        command=['dotnet',str(self.executable),'--urls',self.url]
        if batch is not None:
            path=output/'input.json';path.write_text(batch if raw else json.dumps(batch))
            command += ['--batch-input',str(path),'--batch-output',str(output/'output.json')]
        self.process=subprocess.Popen(command,cwd=folder,env=self.env,stdout=self.log,stderr=self.log)
        try:
            self.wait(lambda: self.ready(), 'host readiness')
        except BaseException:
            self.close();raise
        self.client=base.Client(self.url)
    def ready(self):
        try: return urllib.request.urlopen(self.url+self.ready_path,timeout=1).status==200
        except (urllib.error.URLError,TimeoutError): return False
    def wait(self, predicate, label):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if self.process.poll() is not None: raise RuntimeError((label,'host exited',self.process.returncode))
            value=predicate()
            if value: return value
            time.sleep(.02)
        raise RuntimeError(label+' deadline')
    def batch(self):
        path=self.output/'output.json'
        self.wait(path.exists,'batch completion')
        return json.loads(path.read_text())
    def http(self, raw, index):
        status,body=self.client.request('POST','/fulfillment',raw=raw.encode('utf-8'))
        item={'index':index,'admission':{'status':status,'body':None if status in (400,503) else body}}
        if status==202:
            def completed():
                result=self.client.request('GET',body['resultUrl'])
                return result if result[0]!=202 else None
            result=self.wait(completed,'HTTP completion')
            item['completion']={'status':result[0],'body':result[1]}
        return item
    def facts(self):
        tables={'conventional':('orders','id','inventory','reservations','id'),
                'cohesive':('cohesive_orders','order_id','cohesive_inventory','cohesive_reservations','reservation_id')}
        # Keep the observer read-only and independent of production mappings.
        order,oid,inventory,reservation,rid=tables[self.condition]
        sql=f'''SELECT json_build_object(
        'orders',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT {oid} AS id,status FROM {order}) x),
        'inventory',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT sku,available,max_per_order AS "maxPerOrder",quarantined FROM {inventory}) x),
        'reservations',(SELECT coalesce(json_agg(x),'[]') FROM (SELECT {rid} AS id,order_id AS "orderId",sku,quantity FROM {reservation}) x));'''
        return json.loads(harness.run('docker','exec',self.container,'psql','-U','postgres','-d',self.database,'-At','-c',sql))
    def close(self):
        harness.stop(self.process);self.log.close()

def verify(args):
    args.output.mkdir(parents=True,exist_ok=False)
    container='pv1-'+uuid.uuid4().hex[:12];started=False;condition=None;records={}
    try:
        image=harness.run('docker','image','inspect',harness.IMAGE,'--format','{{.Id}}')
        harness.run('docker','run','-d','--name',container,'-e','POSTGRES_PASSWORD=fixture-only','-p','127.0.0.1::5432',harness.IMAGE);started=True
        for _ in range(100):
            if subprocess.run(['docker','exec',container,'pg_isready','-h','127.0.0.1','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
            time.sleep(.1)
        else: raise RuntimeError('PostgreSQL readiness deadline')
        port=harness.run('docker','port',container,'5432/tcp').rsplit(':',1)[1]
        for condition in ([args.condition] if args.condition else harness.CONDITIONS):
            folder=args.fixtures/condition;fingerprint=build.build_tools.verify_build(folder)
            out=args.output/condition;record={};trace=[]
            def world(name,batch=None,raw=False):return World(folder,out/name,container,port,condition,checks.fixture(),batch,raw)
            items,expected,facts=checks.scenario()
            for mode in ('batch','http'):
                w=world(mode,items if mode=='batch' else None)
                try:
                    result=w.batch()['items'] if mode=='batch' else [w.http(json.dumps(item),i) for i,item in enumerate(items)]
                    record[mode]=checks.check_items(result,expected)
                    observed=w.facts();trace.append({'mode':mode,'items':result,'facts':observed})
                    checks.require(checks.canonical(observed)==checks.canonical(facts),'PV1-04','settled facts',observed)
                    if mode=='batch':
                        checks.require(result[1]['admission']==result[2]['admission'],'PV1-03','retained admission',result[:3])
                        # Change configuration after a retained rejection; replay may not reevaluate it.
                        status,_=w.client.request('POST','/inventory/pv1-quarantine/clear-quarantine')
                        if status!=200: raise RuntimeError(('setup command',status))
                        for index in (1,5):
                            replay=w.http(json.dumps(items[index]),index)
                            checks.require(replay==result[index],'PV1-03','cross-entry replay',(replay,result[index]))
                        before=w.facts()
                        replay_facts=copy.deepcopy(facts)
                        next(x for x in replay_facts['inventory'] if x['sku']=='pv1-quarantine')['quarantined']=False
                        checks.require(checks.canonical(before)==checks.canonical(replay_facts),'PV1-04','replay preservation',before)
                        # Fill the shared host registry, then retain batch identities at capacity.
                        admitted=len({x['admission']['body']['operationId'] for x in result if x['admission']['status']==202})
                        for i in range(1000-admitted):
                            entry=w.http(json.dumps(checks.request('capacity-'+str(i))),i)
                            checks.require(entry['admission']['status']==202,'PV1-03','capacity',entry)
                        checks.require(w.http(json.dumps(checks.request('full')),0)['admission']['status']==503,'PV1-03','capacity','new request at capacity')
                        checks.require(w.http(json.dumps(items[1]),1)==result[1],'PV1-03','cross-entry replay','replay at capacity')
                        checks.require(checks.canonical(w.facts())==checks.canonical(before),'PV1-04','settled facts','capacity writes')
                finally:w.close()
            checks.require(record['batch']==record['http'],'PV1-01','transport parity',record)
            rows=checks.decoding();bindings=checks.binding_examples();binding_start=len(rows)
            rows += [(raw,True) for raw,_ in bindings]
            raw='['+','.join(x[0] for x in rows)+']'
            expected_decode=[{'status':202,'outcome':'OrderMissing'} if valid else {'status':400} for _,valid in rows]
            for mode in ('batch','http'):
                w=world('decode-'+mode,raw if mode=='batch' else None,True)
                try:
                    result=w.batch()['items'] if mode=='batch' else [w.http(raw,i) for i,(raw,_) in enumerate(rows)]
                    checks.check_items(result,expected_decode,'input decoding')
                    for index,(_,intent) in enumerate(bindings,binding_start):
                        replay=w.http(json.dumps(intent),index)
                        checks.require(replay==result[index],'PV1-03','deserialized intent replay',(replay,result[index]))
                    checks.require(checks.canonical(w.facts())==checks.canonical(checks.fixture()),'PV1-04','input preservation',w.facts())
                    trace.append({'mode':'decode-'+mode,'items':result})
                finally:w.close()
            envelopes={'empty':'[]','malformed':'['+json.dumps(items[1])+',','non-array':'{}',
                'oversized':json.dumps([items[1]]*101),'boundary':json.dumps([None]*100)}
            for name,raw in envelopes.items():
                w=world(name,raw,True)
                try:
                    result=w.batch()
                    wanted={'items':[]} if name=='empty' else {'error':'InvalidBatch'}
                    if name=='boundary':
                        checks.require('items' in result,'PV1-02','envelope',result)
                        checks.check_items(result['items'],[{'status':400}]*100)
                    else:checks.require(result==wanted,'PV1-02','envelope',result)
                    checks.require(checks.canonical(w.facts())==checks.canonical(checks.fixture()),'PV1-04','envelope preservation',w.facts())
                    trace.append({'envelope':name,'result':result})
                finally:w.close()
            visible_seed=json.loads((build.ROOT/'batch-seed.json').read_text())
            visible_batch=json.loads((build.ROOT/'batch-examples.json').read_text())
            w=World(folder,out/'visible',container,port,condition,visible_seed,visible_batch)
            try:
                w.batch()
                visible_count=visible_checks.exercise(w.url,w.output/'output.json')
            finally:w.close()
            w=world('files')
            try:
                source=w.output/'input.json';source.write_text(json.dumps(items))
                existing=w.output/'existing.json';existing.write_text('sentinel')
                paths=[['--batch-input',str(source)],
                    ['--batch-output',str(w.output/'unused.json')],
                    ['--batch-input',str(source),'--batch-output',str(source)],
                    ['--batch-input',str(source),'--batch-output',str(existing)],
                    ['--batch-input',str(w.output/'missing.json'),'--batch-output',str(w.output/'unreadable-result.json')],
                    ['--batch-input',str(source),'--batch-output',str(w.output/'missing-directory/result.json')]]
                for index,options in enumerate(paths):
                    with (w.output/f'failure-{index}.log').open('w') as log:
                        result=subprocess.run(['dotnet',str(w.executable),'--urls','http://127.0.0.1:0',*options],
                            cwd=w.folder,env=w.env,stdout=log,stderr=log,timeout=30)
                    checks.require(result.returncode!=0,'PV1-02','operational failure classification',options)
                checks.require(existing.read_text()=='sentinel' and source.read_text()==json.dumps(items),
                    'PV1-04','file preservation','overwritten input/output')
                checks.require(not (w.output/'unreadable-result.json').exists(),'PV1-02','operational failure classification','published failed input')
                checks.require(checks.canonical(w.facts())==checks.canonical(checks.fixture()),'PV1-04','input preservation',w.facts())
                trace.append({'operationalFailures':len(paths)})
            finally:w.close()
            (out/'trace.json').write_text(json.dumps(trace,indent=2)+'\n')
            assert build.build_tools.verify_build(folder)==fingerprint
            records[condition]={'passed':True,'businessItems':len(items),'decodingItemsPerTransport':len(rows),'envelopes':len(envelopes),'operationalFailures':len(paths),'visibleChecks':visible_count,'buildManifestSha256':fingerprint}
        (args.output/'report.json').write_text(json.dumps({'passed':True,'postgresImage':harness.IMAGE,'postgresImageId':image,'conditions':records},indent=2)+'\n')
        print('PV1 passed:',', '.join(records),flush=True)
    except checks.BehavioralFailure as error:
        (args.output/'failure.json').write_text(json.dumps({'kind':'behavioral','condition':condition,'obligation':error.obligation,'assertion':error.assertion,'detail':str(error)},indent=2)+'\n');raise
    except Exception as error:
        (args.output/'failure.json').write_text(json.dumps({'kind':'unqualified','condition':condition,'detail':str(error)},indent=2)+'\n');raise
    finally:
        if started:subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,check=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--condition',choices=harness.CONDITIONS)
    args=parser.parse_args();args.fixtures=args.fixtures.resolve();args.output=args.output.resolve()
    verify(args)
