"""Independent AO1 oracle: public requests and physical facts, no application imports."""
import json

class BehavioralFailure(AssertionError):
    def __init__(self, obligation, assertion, detail):
        self.obligation, self.assertion = obligation, assertion
        super().__init__(str(detail))

def require(ok, obligation, assertion, detail):
    if not ok: raise BehavioralFailure(obligation, assertion, detail)

def canonical(facts):
    return {k: sorted(v, key=lambda x: json.dumps(x, sort_keys=True)) for k, v in facts.items()}

def fixture():
    return {'orders': [dict(id='ao1-'+name, status=status) for name, status in [
        ('archived','Archived'), ('reserved','Archived'), ('draft','Draft'),
        ('submitted','Submitted'), ('cancelled','Cancelled'), ('batch','Draft'),
        ('Case','Draft'), ('case','Archived'), ('sentinel','Draft')]],
        'inventory': [dict(sku='ao1-'+name, available=available, maxPerOrder=limit, quarantined=q)
                      for name, available, limit, q in [('stock',19,8,False), ('quarantined',0,1,True),
                        ('limited',0,1,False), ('empty',0,8,False), ('sentinel',37,4,False)]],
        'reservations': [dict(id='ao1-reserved', orderId='ao1-reserved', sku='ao1-stock', quantity=2)]}

def request(identity, order='archived', sku='stock', quantity=2):
    return dict(requestId='ao1-'+identity, orderId='ao1-'+order, sku='ao1-'+sku, quantity=quantity)

class Checks:
    def __init__(self, world):
        self.world = world
        self.trace = []
        self.expected = fixture()
        self.counts = {}

    def check(self, ok, number, name, detail):
        require(ok, 'AO1-'+number, name, detail)
        self.counts[name] = self.counts.get(name, 0) + 1

    def call(self, method, path, body=None, raw=None):
        status, value = self.world.client.request(method, path, body, raw)
        self.trace.append(dict(method=method, path=path, status=status, body=value))
        if status >= 500: raise RuntimeError(('application failure', status, value))
        return status, value

    def unchanged(self, number, name):
        facts = self.world.facts()
        self.trace.append({'facts': facts})
        self.check(canonical(facts) == canonical(self.expected), number, name, facts)

    def items(self, mode, requests, outcome, number, name):
        if mode == 'batch':
            status, result = self.call('POST', '/fulfillment/batch', requests)
            self.check(status == 200 and isinstance(result, dict) and 'items' in result, number, name, result)
            items = result['items']
        else:
            items = []
            for i, intent in enumerate(requests):
                status, receipt = self.call('POST', '/fulfillment', intent)
                self.check(status == 202, number, name, (status, receipt))
                def done():
                    reply = self.call('GET', receipt['resultUrl'])
                    return reply if reply[0] != 202 else None
                status, result = self.world.wait(done, 'AO1 completion')
                items.append(dict(index=i, admission=dict(status=202, body=receipt),
                                  completion=dict(status=status, body=result)))
        self.check(len(items) == len(requests), number, name, items)
        for i, (item, expected) in enumerate(zip(items, outcome)):
            if item.get('completion', {}).get('status', 0) >= 500:
                raise RuntimeError(('execution failure', item))
            self.check(item.get('index') == i and item.get('admission', {}).get('status') == 202, number, name, item)
            status = 'Submitted' if expected == 'ReservedAndSubmitted' else 'Rejected'
            self.check(item.get('completion') == dict(status=200, body=dict(status=status, outcome=expected)), number, name, item)
        return items

    def run(self):
        try:
            self.check(self.call('POST','/orders/ao1-archived/submit') == (409, {'code':'OrderArchived'}),
                       '01','archived direct submission', self.trace[-1:])
            self.unchanged('01','archived direct submission')
            for order, code in [('submitted','OrderNotDraft'), ('cancelled','OrderCancelled')]:
                self.check(self.call('POST',f'/orders/ao1-{order}/submit') == (409, {'code':code}),
                           '01','existing direct outcomes', self.trace[-1:])
            self.check(self.call('POST','/orders/ao1-missing/submit')[0] == 404, '01','existing direct outcomes',self.trace[-1:])
            self.check(self.call('POST','/orders/ao1-archived/cancel') == (409, {'code':'OrderNotCancellable'}),
                       '01','existing direct outcomes',self.trace[-1:])
            self.check(self.call('POST','/orders/ao1-draft/submit') == (200, {'id':'ao1-draft','status':'Submitted'}),
                       '01','existing direct outcomes',self.trace[-1:])
            next(x for x in self.expected['orders'] if x['id']=='ao1-draft')['status']='Submitted'
            self.unchanged('01','existing direct outcomes')
            # Replay in both directions without altering state/configuration between calls.
            for mode, other in [('http','batch'), ('batch','http')]:
                intent = request(mode)
                original = self.items(mode,[intent],['OrderArchived'],'02','archived fulfillment outcome')
                self.unchanged('02','archived compensation')
                replay = self.items(other,[intent],['OrderArchived'],'05','shared replay and identity')
                self.check(replay == original,'05','shared replay and identity',(original,replay))
                conflict = {**intent,'quantity':3}
                if other == 'http':
                    reply = self.call('POST','/fulfillment',conflict)
                    self.check(reply == (409,{'code':'RequestIdentityConflict'}),'05','shared replay and identity',reply)
                else:
                    status, result = self.call('POST','/fulfillment/batch',[conflict])
                    self.check(status==200 and result=={'items':[{'index':0,'admission':{'status':409,'body':{'code':'RequestIdentityConflict'}}}]},'05','shared replay and identity',result)
                self.unchanged('05','shared replay and identity')
            for i, (order, sku, quantity, outcome) in enumerate([
                ('archived','missing',1,'InventoryMissing'), ('archived','quarantined',0,'InvalidQuantity'),
                ('archived','quarantined',2,'InventoryQuarantined'), ('archived','limited',2,'QuantityLimitExceeded'),
                ('archived','empty',1,'InsufficientStock'), ('reserved','stock',2,'ReservationConflict'),
                ('reserved','missing',0,'ReservationConflict'), ('missing','missing',0,'OrderMissing')]):
                for mode in ('http','batch'):
                    self.items(mode,[request(f'precedence-{mode}-{i}',order,sku,quantity)],[outcome],'03','rejection precedence')
                    self.unchanged('03','rejection precedence')
            # Same spelling except case, different states: a well-typed wrong route selection is observable.
            self.check(self.call('POST','/orders/ao1-case/submit') == (409,{'code':'OrderArchived'}),
                       '04','bound entity identity',self.trace[-1:])
            self.unchanged('04','bound entity identity')
            self.check(self.call('POST','/orders/ao1-Case/submit') == (200,{'id':'ao1-Case','status':'Submitted'}),
                       '04','bound entity identity',self.trace[-1:])
            next(x for x in self.expected['orders'] if x['id']=='ao1-Case')['status']='Submitted'
            self.unchanged('04','bound entity identity')
            # Exercise an actual typed inventory input binding, not only shared DTO binding.
            self.check(self.call('PUT','/inventory/ao1-sentinel/quantity-limit',{'maxPerOrder':3}) ==
                       (200,{'sku':'ao1-sentinel','available':37,'maxPerOrder':3,'quarantined':False}),
                       '04','bound input meaning',self.trace[-1:])
            next(x for x in self.expected['inventory'] if x['sku']=='ao1-sentinel')['maxPerOrder']=3
            self.unchanged('04','bound input meaning')
            self.items('http',[request('input','archived','sentinel',4)],['QuantityLimitExceeded'],'04','bound input meaning')
            self.unchanged('04','bound input meaning')
            # Whole-array decoding must occur before any item executes or retains identity.
            valid = request('decode','batch',quantity=3)
            raw = json.dumps([valid])[:-1]+',{"quantity":{}}]'
            self.check(self.call('POST','/fulfillment/batch',raw=raw.encode())[0]==400,'05','mixed batch preservation',self.trace[-1:])
            self.unchanged('05','mixed batch preservation')
            self.items('batch',[request('mixed'),valid],['OrderArchived','ReservedAndSubmitted'],'05','mixed batch preservation')
            next(x for x in self.expected['orders'] if x['id']=='ao1-batch')['status']='Submitted'
            next(x for x in self.expected['inventory'] if x['sku']=='ao1-stock')['available']-=3
            self.expected['reservations'].append(dict(id='ao1-batch',orderId='ao1-batch',sku='ao1-stock',quantity=3))
            self.unchanged('05','mixed batch preservation')
            self.reads()
            return self.counts
        finally:
            (self.world.output/'trace.json').write_text(json.dumps(self.trace,indent=2)+'\n')

    def reads(self):
        self.check(self.call('GET','/orders/ao1-archived') == (200,dict(id='ao1-archived',status='Archived')),
                   '06','archived read and restart',self.trace[-1:])
        self.check(self.call('GET','/orders/ao1-archived/details') == (200,dict(id='ao1-archived',status='Archived',reservations=[])),
                   '06','archived read and restart',self.trace[-1:])
        self.unchanged('06','archived read and restart')
