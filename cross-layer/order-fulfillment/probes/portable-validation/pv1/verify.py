#!/usr/bin/env python3
"""PV1 process-level checks against both API operations and physical PostgreSQL facts."""
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
from runtime import verification_run

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
        self.initial_batch=batch if raw else json.dumps(batch)
        self.process=subprocess.Popen(command,cwd=folder,env=self.env,stdin=subprocess.DEVNULL,
            stdout=self.log,stderr=self.log)
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
    def send_batch(self, raw):
        status,result=self.client.request('POST','/fulfillment/batch',raw=raw.encode('utf-8'))
        if status>=500:raise RuntimeError(('batch application failure',status,result))
        self.batch_status=status
        return result
    def batch(self):
        (self.output/'input.json').write_text(self.initial_batch)
        result=self.send_batch(self.initial_batch)
        (self.output/'output.json').write_text(json.dumps(result))
        return result
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
    records = {}
    with verification_run(args.output, 'pv1', checks.BehavioralFailure) as session:
        container, port = session.container, session.port
        for condition in ([args.condition] if args.condition else harness.CONDITIONS):
            session.condition = condition
            folder=args.fixtures/condition;fingerprint=build.build_tools.verify_build(folder)
            out=args.output/condition;record={};trace=[]
            def world(name,batch=None,raw=False):return World(folder,out/name,container,port,condition,checks.fixture(),batch,raw)
            items,expected,facts=checks.scenario()
            for mode in ('batch','http'):
                w=world(mode,items if mode=='batch' else None)
                try:
                    result=w.batch()['items'] if mode=='batch' else [w.http(json.dumps(item),i) for i,item in enumerate(items)]
                    if mode=='batch':checks.require(w.batch_status==200,'PV1-02','batch status',w.batch_status)
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
                        batch_result=w.send_batch(json.dumps([checks.request('full'),items[1],checks.request('capacity-'+str(999-admitted))]))['items']
                        checks.require(batch_result[0]=={'index':0,'admission':{'status':503,'body':None}},'PV1-03','batch capacity',batch_result)
                        checks.require(batch_result[1]==result[1],'PV1-03','cross-entry replay',batch_result)
                        checks.require(batch_result[2]=={**entry,'index':2},'PV1-03','single-to-batch replay',batch_result)
                        checks.require(checks.canonical(w.facts())==checks.canonical(before),'PV1-04','settled facts','capacity writes')
                        checks.require(w.batch_status==200,'PV1-02','batch status',w.batch_status)
                finally:w.close()
            checks.require(record['batch']==record['http'],'PV1-01','transport parity',record)
            rows=checks.decoding();bindings=checks.binding_examples()
            rows += [(raw,True,True) for raw,_ in bindings]
            for mode in ('batch','http'):
                w=world('decode-'+mode)
                try:
                    results=[]
                    for index,(raw,valid,decodable) in enumerate(rows):
                        expected={'status':202,'outcome':'OrderMissing'} if valid else {'status':400}
                        if mode=='http':
                            result=w.http(raw,0)
                        elif decodable:
                            reply=w.send_batch('['+raw+']')
                            checks.require(w.batch_status==200,'PV1-01','input decoding',reply)
                            result=reply['items'][0]
                        else:
                            # A valid first item must not execute or retain an identity
                            # when a later item cannot bind to the typed array.
                            prefix=checks.request('decode-prefix-'+str(index),'success')
                            reply=w.send_batch('['+json.dumps(prefix)+','+raw+']')
                            checks.require(w.batch_status==400,'PV1-01','input decoding',reply)
                            checks.require(checks.canonical(w.facts())==checks.canonical(checks.fixture()),'PV1-04','input preservation',w.facts())
                            retry=w.http(json.dumps({**prefix,'orderId':'pv1-missing'}),0)
                            checks.check_items([retry],[{'status':202,'outcome':'OrderMissing'}],'input decoding')
                            results.append({'status':400});continue
                        checks.check_items([result],[expected],'input decoding')
                        results.append(result)
                    for raw,intent in bindings:
                        reply=w.send_batch('['+raw+']')
                        checks.require(w.batch_status==200,'PV1-01','input decoding',reply)
                        replay=w.http(json.dumps(intent),0)
                        checks.require(replay==reply['items'][0],'PV1-03','deserialized intent replay',(replay,reply))
                    checks.require(checks.canonical(w.facts())==checks.canonical(checks.fixture()),'PV1-04','input preservation',w.facts())
                    trace.append({'mode':'decode-'+mode,'items':results})
                finally:w.close()
            envelopes={'empty':'[]','malformed':'['+json.dumps(items[1])+',','non-array':'{}',
                'oversized':json.dumps([items[1]]*101),'boundary':json.dumps([None]*100)}
            for name,raw in envelopes.items():
                w=world(name,raw,True)
                try:
                    result=w.batch()
                    wanted={'items':[]} if name=='empty' else {'error':'InvalidBatch'}
                    checks.require(w.batch_status==(200 if name in ('empty','boundary') else 400),'PV1-02','envelope',w.batch_status)
                    if name=='boundary':
                        checks.require('items' in result,'PV1-02','envelope',result)
                        checks.check_items(result['items'],[{'status':400}]*100)
                    elif name not in ('malformed','non-array'):checks.require(result==wanted,'PV1-02','envelope',result)
                    checks.require(checks.canonical(w.facts())==checks.canonical(checks.fixture()),'PV1-04','envelope preservation',w.facts())
                    checks.require(w.send_batch('[]')=={'items':[]} and w.batch_status==200,'PV1-02','request recovery','next request failed')
                    trace.append({'envelope':name,'result':result})
                finally:w.close()
            visible_seed=json.loads((build.ROOT/'batch-seed.json').read_text())
            visible_batch=json.loads((build.ROOT/'batch-examples.json').read_text())
            w=World(folder,out/'visible',container,port,condition,visible_seed,visible_batch)
            try:
                visible_count=visible_checks.exercise(w.url)
            finally:w.close()
            (out/'trace.json').write_text(json.dumps(trace,indent=2)+'\n')
            assert build.build_tools.verify_build(folder)==fingerprint
            records[condition]={'passed':True,'businessItems':len(items),'decodingItemsPerOperation':len(rows),'envelopes':len(envelopes),'requestRecoveryCases':len(envelopes),'visibleChecks':visible_count,'buildManifestSha256':fingerprint}
        session.report(records)
    print('PV1 passed:', ', '.join(records), flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--condition',choices=harness.CONDITIONS)
    args=parser.parse_args();args.fixtures=args.fixtures.resolve();args.output=args.output.resolve()
    verify(args)
