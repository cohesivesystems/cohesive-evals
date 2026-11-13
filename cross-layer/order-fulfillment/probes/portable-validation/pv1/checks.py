"""Independent PV1 fixtures and expectations; no application/schema imports."""
import copy
import json

class BehavioralFailure(AssertionError):
    def __init__(self, obligation, assertion, detail):
        self.obligation, self.assertion = obligation, assertion
        super().__init__(str(detail))

def require(ok, obligation, assertion, detail):
    if not ok:
        raise BehavioralFailure(obligation, assertion, detail)

def request(identity, order='missing', sku='stock', quantity=1):
    return dict(requestId='pv1-'+identity, orderId='pv1-'+order, sku='pv1-'+sku, quantity=quantity)

def fixture():
    return {'orders':[{'id':'pv1-'+name, 'status':status} for name,status in [
        ('success','Draft'), ('invalid','Draft'), ('quarantine','Draft'), ('limit','Draft'),
        ('short','Draft'), ('missing-sku','Draft'), ('cancelled','Cancelled'), ('submitted','Submitted'),
        ('matched','Submitted'), ('conflict','Submitted'), ('first','Draft'), ('second','Draft'), ('sentinel','Draft')]],
        'inventory':[{'sku':'pv1-'+name,'available':stock,'maxPerOrder':limit,'quarantined':q} for name,stock,limit,q in [
            ('stock',10,2147483647,False), ('quarantine',0,1,True), ('limit',0,1,False),
            ('empty',0,2147483647,False), ('ordered',3,2147483647,False), ('sentinel',13,4,False)]],
        'reservations':[{'id':'pv1-'+name,'orderId':'pv1-'+name,'sku':'pv1-stock','quantity':1} for name in ('matched','conflict')]}

def scenario():
    items=[None, request('success','success',quantity=2), request('success','success',quantity=2),
        request('success','success',quantity=3), request('invalid','invalid','quarantine',0),
        request('q','quarantine','quarantine',2), request('limit','limit','limit',2),
        request('short','short','empty'), request('sku','missing-sku','missing'), request('missing'),
        request('cancel','cancelled'), request('submitted','submitted'), request('matched','matched'),
        request('conflict','conflict',quantity=2), request('first','first','ordered',2),
        request('second','second','ordered',2), request('new-identity','success',quantity=2)]
    outcomes=[None,'ReservedAndSubmitted','ReservedAndSubmitted',None,'InvalidQuantity',
        'InventoryQuarantined','QuantityLimitExceeded','InsufficientStock','InventoryMissing','OrderMissing',
        'OrderCancelled','OrderRejected','ReservedAndSubmitted','ReservationConflict',
        'ReservedAndSubmitted','InsufficientStock','ReservedAndSubmitted']
    expected=[]
    for index,outcome in enumerate(outcomes):
        if index==0: expected.append({'status':400})
        elif index==3: expected.append({'status':409,'code':'RequestIdentityConflict'})
        else: expected.append({'status':202,'outcome':outcome})
    facts=copy.deepcopy(fixture())
    for order in facts['orders']:
        if order['id'] in ('pv1-success','pv1-first'): order['status']='Submitted'
    for stock in facts['inventory']:
        if stock['sku'] in ('pv1-stock','pv1-ordered'): stock['available']-=2
    facts['reservations'] += [dict(id='pv1-'+o,orderId='pv1-'+o,sku='pv1-'+s,quantity=2) for o,s in [('success','stock'),('first','ordered')]]
    return items,expected,facts

def decoding():
    # JSON text, not Python floats: keep exact fractional and exponent witnesses.
    template='{"requestId":"pv1-decode-%d","orderId":"pv1-missing","sku":"pv1-stock","quantity":%s}'
    quantities=[('1',True),('1.0',False),('1e0',False),('2147483647',True),('-2147483648',True),
        ('0',True),('-1',True),('true',False),('"1"',True),('1.5',False),('2147483648',False),
        ('-2147483649',False),('1.00000000000000000000000000001',False),('1e999',False),('0e999',False),('null',False),('"1.0"',False),('"1e0"',False),('"2147483648"',False)]
    rows=[(template%(i,q),valid) for i,(q,valid) in enumerate(quantities)]
    normal=template%(99,'1')
    rows += [(raw,False) for raw in ['null','[]','true','3','{}',
        normal.replace('"pv1-decode-99"','null'),normal.replace('"pv1-decode-99"','"  "'),
        normal.replace(',"quantity":1','')]]
    rows += [(normal.replace('"pv1-decode-99"','"pv1-😀"')[:-1]+',"extra":42}',True)]
    return rows

def binding_examples():
    # Independently authored typed intents: verify values through cross-entry replay,
    # not just acceptance or identical domain outcomes for a missing order.
    canonical=request('binding')
    return [
        (json.dumps({k.upper():v for k,v in canonical.items()}),canonical),
        (json.dumps({**canonical,'quantity':'1'}),canonical),
        ('{"requestId":"ignored","REQUESTID":"pv1-binding","orderId":"pv1-missing",'
         '"sku":"pv1-stock","quantity":2,"quantity":1}',canonical),
        (json.dumps({**canonical,'extra':{'ignored':True}}),canonical),
    ]


def canonical(facts):
    return {k:sorted(v,key=lambda x:json.dumps(x,sort_keys=True)) for k,v in facts.items()}

def check_items(items, expected, assertion='outcomes'):
    require(len(items)==len(expected),'PV1-02','ordered results',(len(items),len(expected)))
    normalized=[]
    for index,(item,want) in enumerate(zip(items,expected)):
        require(item.get('index')==index,'PV1-02','ordered results',item)
        admission=item.get('admission',{})
        status=admission.get('status')
        if status is not None and status>=500 and status!=503: raise RuntimeError(('application failure',item))
        completion=item.get('completion')
        if completion and completion.get('status',0)>=500: raise RuntimeError(('application execution failure',item))
        require(status==want['status'],'PV1-01',assertion,(index,item,want))
        if status==202:
            require(isinstance(admission.get('body'),dict) and set(admission['body'])=={'operationId','resultUrl'},'PV1-03','admission shape',item)
            expected_body={'status':'Submitted' if want['outcome']=='ReservedAndSubmitted' else 'Rejected','outcome':want['outcome']}
            require(completion=={'status':200,'body':expected_body},'PV1-01',assertion,(index,item,want))
            normalized.append((202,expected_body))
        else:
            body={'code':want['code']} if 'code' in want else None
            require(admission.get('body')==body and 'completion' not in item,'PV1-02','item failure',item)
            normalized.append((status,body))
    return normalized
