"""Independent settled-state E1 model and targeted contract witnesses."""
import copy
import json
import random
import time

class BehavioralFailure(AssertionError):
    def __init__(self, obligation, detail):
        self.obligation=obligation
        self.assertion=detail[0] if isinstance(detail,tuple) else detail
        super().__init__(f'{obligation}: {detail}')


def require(ok, obligation, detail):
    if not ok: raise BehavioralFailure(obligation, detail)


def fixture():
    return {'orders':[{'id':f'e1-{i}','status':'Submitted' if i==19 else 'Draft'} for i in range(20)],
            'inventory':[{'sku':'e1-stock','available':12}, {'sku':'e1-other','available':7,'maxPerOrder':2},
                         {'sku':'e1-sentinel','available':13,'maxPerOrder':4},
                         {'sku':'e1-max','available':2147483647}], 'reservations':[]}


class Checks:
    def __init__(self, Client, url, observe, output):
        self.c=Client(url);self.observe=observe;self.output=output;self.trace=[]
        data=fixture()
        self.state={'orders':copy.deepcopy(data['orders']),
                    'inventory':[{**x,'maxPerOrder':x.get('maxPerOrder',2147483647)} for x in data['inventory']],
                    'reservations':[]}
        self.history={};self.counter=0

    def http(self, method, path, body=None, raw=None):
        result=self.c.request(method,path,body,raw)
        if result[0]>=500: raise RuntimeError(f'Application execution/host failure: {method} {path}: {result}')
        return result

    def record(self, obligation, command, observed, assertion="settled facts/preservation"):
        facts=self.observe()
        canonical=lambda state:{k:sorted(v,key=lambda x:json.dumps(x,sort_keys=True)) for k,v in state.items()}
        entry={'obligation':obligation,'command':command,'observed':observed,'expectedFacts':copy.deepcopy(self.state),'facts':facts}
        self.trace.append(entry)
        (self.output/'e1-trace.json').write_text(json.dumps(self.trace,indent=2)+'\n')
        require(canonical(facts)==canonical(self.state),obligation,(assertion,entry))

    def inventory(self, sku): return next((x for x in self.state['inventory'] if x['sku']==sku),None)
    def order(self, id): return next((x for x in self.state['orders'] if x['id']==id),None)

    def configure(self, sku, value):
        item=self.inventory(sku)
        response=self.http('PUT',f'/inventory/{sku}/quantity-limit',{'maxPerOrder':value})
        expected=(200,{**item,'maxPerOrder':value}) if item else (404,None)
        require(response[0]==expected[0] and (not item or response[1]==expected[1]),'E1-01',('configure',response,expected))
        if item: item['maxPerOrder']=value
        self.record('E1-01',{'put':sku,'value':value},response)

    def new_request(self, order, sku, quantity, witness="fulfillment outcome"):
        self.counter+=1
        request={'requestId':f'e1-request-{self.counter}','orderId':order,'sku':sku,'quantity':quantity}
        item=self.inventory(sku);entity=self.order(order)
        existing=next((r for r in self.state['reservations'] if r['orderId']==order),None)
        if not entity: outcome='OrderMissing'
        elif existing:
            outcome='ReservedAndSubmitted' if existing['sku']==sku and existing['quantity']==quantity and entity['status']=='Submitted' else 'ReservationConflict'
        elif not item: outcome='InventoryMissing'
        elif quantity<=0: outcome='InvalidQuantity'
        elif quantity>item['maxPerOrder']: outcome='QuantityLimitExceeded'
        elif quantity>item['available']: outcome='InsufficientStock'
        elif entity['status']!='Draft': outcome='OrderRejected'
        else:
            outcome='ReservedAndSubmitted';entity['status']='Submitted';item['available']-=quantity
            self.state['reservations'].append({'id':order,'orderId':order,'sku':sku,'quantity':quantity})
        response=self.http('POST','/fulfillment',request)
        require(response[0]==202,'E1-02',('admission',response))
        receipt=response[1];deadline=time.monotonic()+20
        while True:
            result=self.http('GET',receipt['resultUrl'])
            if result[0]!=202: break
            if time.monotonic()>deadline: raise RuntimeError('Fulfillment did not complete')
            time.sleep(.02)
        expected={'status':'Submitted' if outcome=='ReservedAndSubmitted' else 'Rejected','outcome':outcome}
        require(result==(200,expected),'E1-02',(witness,request,result,expected))
        self.history[request['requestId']]=(request,receipt,expected)
        self.record('E1-02',request,result,witness)
        return request['requestId']

    def replay(self, key):
        request,receipt,completion=self.history[key]
        require(self.http('POST','/fulfillment',request)==(202,receipt),'E1-03','retained admission')
        require(self.http('GET',receipt['resultUrl'])==(200,completion),'E1-03','retained completion')
        conflict=self.http('POST','/fulfillment',{**request,'quantity':0 if request['quantity'] != 0 else 1})
        require(conflict==(409,{'code':'RequestIdentityConflict'}),'E1-03','identity conflict')
        self.record('E1-03',{'replay':key},completion)

    def run(self):
        for item in self.state['inventory']:
            require(self.http('GET','/inventory/'+item['sku'])==(200,item),'E1-01','seed/default/read')
        self.record('E1-01','initial seed',None)
        invalid=[b'',b'null',b'[]',b'{}',b'{',b'{"maxPerOrder":null}',b'{"maxPerOrder":true}',
                 b'{"maxPerOrder":"2"}',b'{"maxPerOrder":0}',b'{"maxPerOrder":-1}',
                 b'{"maxPerOrder":1.5}',b'{"maxPerOrder":2147483648}',b'{"MaxPerOrder":2}',
                 b'{"maxPerOrder":1.00000000000000000000000000000000001}',b'{"maxPerOrder":1e999}']
        for sku in ['e1-stock','e1-missing']:
            for raw in invalid:
                response=self.http('PUT',f'/inventory/{sku}/quantity-limit',raw=raw)
                require(response[0]==400,'E1-01',('invalid input before lookup',sku,raw.decode(),response))
                self.record('E1-01',{'invalid':raw.decode(),'sku':sku},response[0])
        for raw in [b'{"maxPerOrder":1.0}',b'{"maxPerOrder":1e0}',b'{"maxPerOrder":10e-1}',b'{"maxPerOrder":1,"extra":42}']:
            response=self.http('PUT','/inventory/e1-stock/quantity-limit',raw=raw)
            self.inventory('e1-stock')['maxPerOrder']=1
            require(response==(200,self.inventory('e1-stock')),'E1-01',('integral input',response))
            self.record('E1-01',raw.decode(),response)
        self.configure('e1-missing',2)
        self.configure('e1-stock',2);self.configure('e1-stock',2)
        reject=self.new_request('e1-0','e1-stock',3,'limit enforcement')
        good=self.new_request('e1-1','e1-stock',2,'inclusive boundary')
        self.configure('e1-stock',1)
        self.replay(good);self.replay(reject)
        self.new_request('e1-1','e1-stock',2) # Matching reservation precedes new limit.
        self.new_request('e1-1','e1-stock',3) # Conflict precedes new limit.
        self.new_request('e1-missing','e1-missing',0)
        self.new_request('e1-2','e1-missing',0)
        self.new_request('e1-2','e1-stock',0)
        self.new_request('e1-2','e1-stock',2147483647,'limit before shortage') # Limit before shortage.
        self.new_request('e1-19','e1-stock',3) # Limit before lifecycle.
        self.new_request('e1-19','e1-stock',1,'lifecycle rejection preserves stock') # Reachable compensation/settled rejection.
        self.configure('e1-stock',2147483647)
        self.replay(reject)
        self.new_request('e1-2','e1-stock',11) # Shortage before lifecycle.
        self.configure('e1-max',2147483647)
        self.new_request('e1-18','e1-max',2147483647)
        rng=random.Random(161)
        for _ in range(60):
            kind=rng.randrange(3)
            if kind==0: self.configure(rng.choice(['e1-stock','e1-other']),rng.choice([1,2,4,2147483647]))
            elif kind==1: self.new_request('e1-'+str(rng.randrange(18)),rng.choice(['e1-stock','e1-other']),rng.choice([-1,0,1,2,3,9]))
            else: self.replay(rng.choice(list(self.history)))
        return {'commands':len(self.trace),'finalFacts':self.state}

    def after_restart(self):
        self.record('E1-01','clean restart',None)
        for item in self.state['inventory']:
            require(self.http('GET','/inventory/'+item['sku'])==(200,item),'E1-01','persistent limit view')
        self.history.clear() # No request-history guarantee across restart.
        self.counter+=1000
        self.new_request('e1-19','e1-other',1)
