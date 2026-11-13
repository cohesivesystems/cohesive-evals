"""Independent settled-state E2 model and targeted contract witnesses."""
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
    return {'orders':[{'id':f'e2-{i}','status':'Submitted' if i==19 else ('Cancelled' if i==18 else 'Draft')} for i in range(20)],
            'inventory':[{'sku':'e2-stock','available':12}, {'sku':'e2-other','available':7,'maxPerOrder':2},
                         {'sku':'e2-sentinel','available':13,'maxPerOrder':4},
                         {'sku':'e2-max','available':2147483647}], 'reservations':[]}


class Checks:
    prefix = 'e2'
    seed_fixture = staticmethod(fixture)
    inventory_defaults = {'maxPerOrder': 2147483647}
    fulfillment_obligation = 'E2-02'
    replay_obligation = 'E2-03'

    def __init__(self, Client, url, observe, output):
        self.c=Client(url);self.observe=observe;self.output=output;self.trace=[]
        data=self.seed_fixture()
        self.state={'orders':copy.deepcopy(data['orders']),
                    'inventory':[{**self.inventory_defaults, **x} for x in data['inventory']],
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
        (self.output/f'{self.prefix}-trace.json').write_text(json.dumps(self.trace,indent=2)+'\n')
        require(canonical(facts)==canonical(self.state),obligation,(assertion,entry))

    def inventory(self, sku): return next((x for x in self.state['inventory'] if x['sku']==sku),None)
    def order(self, id): return next((x for x in self.state['orders'] if x['id']==id),None)

    def configure(self, sku, value):
        item=self.inventory(sku)
        response=self.http('PUT',f'/inventory/{sku}/quantity-limit',{'maxPerOrder':value})
        expected=(200,{**item,'maxPerOrder':value}) if item else (404,None)
        require(response[0]==expected[0] and (not item or response[1]==expected[1]),'E2-01',('configure',response,expected))
        if item: item['maxPerOrder']=value
        self.record('E2-01',{'put':sku,'value':value},response)

    def inventory_rejection(self, item, quantity):
        """Inventory decisions after positive-quantity validation, before lifecycle."""
        if quantity > item['maxPerOrder']:
            return 'QuantityLimitExceeded'
        if quantity > item['available']:
            return 'InsufficientStock'
        return None

    def new_request(self, order, sku, quantity, witness="fulfillment outcome"):
        self.counter+=1
        request={'requestId':f'{self.prefix}-request-{self.counter}','orderId':order,'sku':sku,'quantity':quantity}
        item=self.inventory(sku);entity=self.order(order)
        existing=next((r for r in self.state['reservations'] if r['orderId']==order),None)
        if not entity: outcome='OrderMissing'
        elif existing:
            outcome='ReservedAndSubmitted' if existing['sku']==sku and existing['quantity']==quantity and entity['status']=='Submitted' else 'ReservationConflict'
        elif not item: outcome='InventoryMissing'
        elif quantity<=0: outcome='InvalidQuantity'
        elif (rejection := self.inventory_rejection(item, quantity)) is not None: outcome=rejection
        elif entity['status']=='Cancelled': outcome='OrderCancelled'
        elif entity['status']!='Draft': outcome='OrderRejected'
        else:
            outcome='ReservedAndSubmitted';entity['status']='Submitted';item['available']-=quantity
            self.state['reservations'].append({'id':order,'orderId':order,'sku':sku,'quantity':quantity})
        response=self.http('POST','/fulfillment',request)
        require(response[0]==202,self.fulfillment_obligation,('admission',response))
        receipt=response[1];deadline=time.monotonic()+20
        while True:
            result=self.http('GET',receipt['resultUrl'])
            if result[0]!=202: break
            if time.monotonic()>deadline: raise RuntimeError('Fulfillment did not complete')
            time.sleep(.02)
        expected={'status':'Submitted' if outcome=='ReservedAndSubmitted' else 'Rejected','outcome':outcome}
        require(result==(200,expected),self.fulfillment_obligation,(witness,request,result,expected))
        self.history[request['requestId']]=(request,receipt,expected)
        self.record(self.fulfillment_obligation,request,result,witness)
        return request['requestId']

    def replay(self, key):
        request,receipt,completion=self.history[key]
        require(self.http('POST','/fulfillment',request)==(202,receipt),self.replay_obligation,'retained admission')
        require(self.http('GET',receipt['resultUrl'])==(200,completion),self.replay_obligation,'retained completion')
        conflict=self.http('POST','/fulfillment',{**request,'quantity':0 if request['quantity'] != 0 else 1})
        require(conflict==(409,{'code':'RequestIdentityConflict'}),self.replay_obligation,'identity conflict')
        self.record(self.replay_obligation,{'replay':key},completion)

    def cancel(self, order, raw=None, witness="cancellation state table"):
        entity = self.order(order)
        response = self.http('POST', f'/orders/{order}/cancel', raw=raw)
        if entity is None:
            expected = (404, None)
        elif entity['status'] in ('Draft', 'Cancelled'):
            expected = (200, {'id': order, 'status': 'Cancelled'})
        else:
            expected = (409, {'code': 'OrderNotCancellable'})
        require(response == expected, 'E2-01', (witness, response, expected))
        if entity and expected[0] == 200:
            entity['status'] = 'Cancelled'
        self.record('E2-01', {'cancel': order}, response, 'cancellation preservation')
        if entity:
            self.views(order)

    def views(self, order):
        entity = self.order(order)
        rows = [{'id': r['id'], 'sku': r['sku'], 'quantity': r['quantity'],
                 'availableStock': self.inventory(r['sku'])['available']}
                for r in self.state['reservations'] if r['orderId'] == order]
        require(self.http('GET', f'/orders/{order}') == (200, entity),
                'E2-01', 'summary status')
        require(self.http('GET', f'/orders/{order}/details') == (200, {**entity, 'reservations': rows}),
                'E2-01', 'details status')

    def submit(self, order):
        entity = self.order(order)
        if entity is None:
            expected = (404, None)
        elif entity['status'] == 'Cancelled':
            expected = (409, {'code': 'OrderCancelled'})
        elif entity['status'] == 'Submitted':
            expected = (409, {'code': 'OrderNotDraft'})
        else:
            expected = (200, {'id': order, 'status': 'Submitted'})
        response = self.http('POST', f'/orders/{order}/submit')
        require(response == expected, 'E2-02', ('direct submit outcome', response, expected))
        if entity and expected[0] == 200:
            entity['status'] = 'Submitted'
        self.record('E2-02', {'submit': order}, response)

    def run(self):
        self.record('E2-01', 'seed', None)
        self.views('e2-18') # Seeded terminal state is supported.
        self.cancel('e2-missing', raw=b'{')
        self.cancel('e2-19')
        self.cancel('e2-0', raw=b'{') # Body is deliberately ignored.
        self.cancel('e2-0', raw=b'null', witness='idempotent cancellation')
        self.submit('e2-0')
        self.submit('e2-18')
        self.configure('e2-stock', 2)
        self.new_request('e2-0', 'e2-missing', 0, 'missing inventory before cancellation')
        self.new_request('e2-0', 'e2-stock', 0, 'invalid quantity before cancellation')
        self.new_request('e2-0', 'e2-stock', 13, 'limit before cancellation')
        self.configure('e2-stock', 2147483647)
        self.new_request('e2-0', 'e2-stock', 13, 'shortage before cancellation')
        self.new_request('e2-0', 'e2-stock', 1, 'cancelled fulfillment')
        self.new_request('e2-18', 'e2-stock', 1, 'cancelled fulfillment')
        rejected = self.new_request('e2-1', 'e2-other', 3)
        self.cancel('e2-1')
        self.replay(rejected)
        self.configure('e2-other', 4)
        self.replay(rejected)
        self.new_request('e2-1', 'e2-other', 3, 'cancelled fulfillment')
        success = self.new_request('e2-2', 'e2-stock', 2)
        self.cancel('e2-2') # Cannot cancel an order with a completed reservation.
        self.replay(success)
        self.new_request('e2-2', 'e2-stock', 2)
        self.new_request('e2-2', 'e2-stock', 1)
        self.submit('e2-3')
        self.cancel('e2-3')
        rng = random.Random(162)
        for _ in range(60):
            kind = rng.randrange(5)
            order = 'e2-' + str(rng.randrange(18))
            if kind == 0:
                self.cancel(order)
            elif kind == 1:
                self.submit(order)
            elif kind == 2:
                self.configure(rng.choice(['e2-stock', 'e2-other']), rng.choice([1, 2, 4, 2147483647]))
            elif kind == 3:
                self.new_request(order, rng.choice(['e2-stock', 'e2-other']), rng.choice([-1, 0, 1, 2, 9]))
            else:
                self.replay(rng.choice(list(self.history)))
        return {'commands': len(self.trace), 'finalFacts': self.state}

    def after_restart(self):
        self.record('E2-01', 'clean restart', None)
        for entity in self.state['orders']:
            self.views(entity['id'])
        self.history.clear() # Host-lifetime results need not survive.
        self.counter += 1000
        self.cancel('e2-0')
        self.submit('e2-0')
        self.new_request('e2-0', 'e2-other', 1, 'cancelled fulfillment')
