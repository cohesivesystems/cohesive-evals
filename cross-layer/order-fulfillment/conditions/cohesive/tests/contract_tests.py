#!/usr/bin/env python3
"""Visible HTTP behavior checks. Run against a fresh, seeded fulfillment host."""
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request

SEED = {
 'orders':[{'id':x, 'status':'Submitted' if x in ['submitted','matched','direct-submitted'] else 'Draft'} for x in
           ['success','submitted','invalid','insufficient','missing-sku','matched','conflict','direct','direct-submitted','case-A','case-a','unrelated']],
 'inventory':[{'sku':x,'available':5} for x in ['success-sku','submitted-sku','invalid-sku','insufficient-sku','matched-sku','conflict-sku','unrelated-sku']],
 'reservations':[
  {'id':'matched','orderId':'matched','sku':'matched-sku','quantity':2},
  {'id':'conflict','orderId':'conflict','sku':'conflict-sku','quantity':1}]
}

class Client:
 def __init__(self,url):
  self.url=url;self.observations=[]
 def request(self,method,path,body=None,raw=None):
  data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
  req=urllib.request.Request(self.url+path,data=data,method=method,headers={'Content-Type':'application/json'})
  try: response=urllib.request.urlopen(req,timeout=20)
  except urllib.error.HTTPError as error: response=error
  payload=response.read()
  try: result=json.loads(payload) if payload else None
  except json.JSONDecodeError: result=payload.decode()
  return response.status,result
 def expect(self,label,method,path,status,body=None,expected=None,raw=None):
  actual,value=self.request(method,path,body,raw)
  assert actual==status,(label,actual,value)
  if expected is not None: assert value==expected,(label,value,expected)
  self.observations.append({'check':label,'status':actual,'body':value})
  return value
 def fulfill(self,label,order,sku,quantity,outcome):
  request={'requestId':label,'orderId':order,'sku':sku,'quantity':quantity}
  status,receipt=self.request('POST','/fulfillment',request)
  assert status==202,(label,status,receipt)
  assert set(receipt)=={'operationId','resultUrl'} and receipt['resultUrl']=='/fulfillment/results/'+receipt['operationId']
  end=time.monotonic()+20
  while True:
   status,value=self.request('GET',receipt['resultUrl'])
   if status!=202: break
   assert time.monotonic()<end,('poll timeout',label)
   time.sleep(.02)
  expected={'status':'Submitted' if outcome=='ReservedAndSubmitted' else 'Rejected','outcome':outcome}
  assert (status,value)==(200,expected),(label,status,value,expected)
  status,replayed=self.request('POST','/fulfillment',request)
  assert status==202 and replayed==receipt,('admission replay',label,status,replayed)
  assert self.request('GET',receipt['resultUrl'])==(200,expected)
  self.observations.append({'check':label,'status':200,'body':value})
  return request,receipt

def exercise(url):
 c=Client(url)
 c.expect('empty details','GET','/orders/success/details',200,expected={'id':'success','status':'Draft','reservations':[]})
 c.expect('empty availability','GET','/orders/success/availability',200,expected=[])
 for path in ['/orders/unknown','/orders/unknown/details','/orders/unknown/availability','/inventory/unknown','/fulfillment/results/unknown']:
  c.expect('not found '+path,'GET',path,404)
 c.expect('missing direct submit','POST','/orders/unknown/submit',404)
 c.expect('direct submit','POST','/orders/direct/submit',200,expected={'id':'direct','status':'Submitted'})
 c.expect('direct reject','POST','/orders/direct/submit',409,expected={'code':'OrderNotDraft'})
 c.expect('direct no reservation','GET','/orders/direct/availability',200,expected=[])
 c.expect('case sensitive id','POST','/orders/case-A/submit',200,expected={'id':'case-A','status':'Submitted'})
 c.expect('other case preserved','GET','/orders/case-a',200,expected={'id':'case-a','status':'Draft'})
 status,created=c.request('POST','/orders')
 assert status==201 and set(created)=={'id'} and created['id']
 assert c.request('GET','/orders/'+created['id'])==(200,{'id':created['id'],'status':'Draft'})
 c.observations.append({'check':'create','status':201,'body':{'id':'<created>'}})
 for label,body in [('empty request',{'requestId':'','orderId':'success','sku':'success-sku','quantity':1}),
                    ('empty order',{'requestId':'empty-order','orderId':'','sku':'success-sku','quantity':1}),
                    ('null sku',{'requestId':'null-sku','orderId':'success','sku':None,'quantity':1})]:
  c.expect(label,'POST','/fulfillment',400,body)
 for body in [b'{',b'{"requestId":"missing","orderId":"success","sku":"success-sku"}',
              b'{"requestId":"overflow","orderId":"success","sku":"success-sku","quantity":2147483648}']:
  status,_=c.request('POST','/fulfillment',raw=body);assert status==400,(body,status)
 c.observations.append({'check':'malformed and missing quantities','status':400})
 c.fulfill('unknown-precedence','unknown','unknown',0,'OrderMissing')
 c.fulfill('missing-inventory-precedence','missing-sku','unknown',0,'InventoryMissing')
 c.fulfill('invalid-zero','invalid','invalid-sku',0,'InvalidQuantity')
 c.fulfill('invalid-negative','invalid','invalid-sku',-2147483648,'InvalidQuantity')
 c.fulfill('insufficient','insufficient','insufficient-sku',6,'InsufficientStock')
 c.fulfill('submitted-stock-precedence','submitted','submitted-sku',6,'InsufficientStock')
 c.fulfill('submitted-compensation','submitted','submitted-sku',2,'OrderRejected')
 c.fulfill('existing-match','matched','matched-sku',2,'ReservedAndSubmitted')
 c.fulfill('existing-conflict-precedence','conflict','unknown',0,'ReservationConflict')
 request,receipt=c.fulfill('success-request','success','success-sku',2,'ReservedAndSubmitted')
 c.fulfill('same-intent-new-request','success','success-sku',2,'ReservedAndSubmitted')
 # Identical concurrent admissions reuse the same completed operation and do not
 # run work again. This is not an independent-intent concurrency claim.
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  duplicate=list(pool.map(lambda _:c.request('POST','/fulfillment',request),range(8)))
 assert all(item==(202,receipt) for item in duplicate)
 c.expect('changed request identity','POST','/fulfillment',409,{**request,'quantity':3},expected={'code':'RequestIdentityConflict'})
 c.expect('success stock','GET','/inventory/success-sku',200,expected={'sku':'success-sku','available':3})
 c.expect('compensated stock','GET','/inventory/submitted-sku',200,expected={'sku':'submitted-sku','available':5})
 c.expect('rejected reservations','GET','/orders/submitted/availability',200,expected=[])
 c.expect('success details','GET','/orders/success/details',200,expected={'id':'success','status':'Submitted','reservations':[
   {'id':'success','sku':'success-sku','quantity':2,'availableStock':3}]})
 c.expect('success availability','GET','/orders/success/availability',200,expected=[{'reservationId':'success','sku':'success-sku','quantity':2,'availableStock':3}])
 for sku in ['invalid-sku','insufficient-sku','matched-sku','conflict-sku','unrelated-sku']:
  c.expect('preserved '+sku,'GET','/inventory/'+sku,200,expected={'sku':sku,'available':5})
 c.expect('unrelated order','GET','/orders/unrelated',200,expected={'id':'unrelated','status':'Draft'})
 c.expect('seed not on listener','POST','/seed',404,{})
 return c.observations

if __name__=='__main__':
 if sys.argv[1:] == ['--seed']:
  print(json.dumps(SEED,indent=2))
 else:
  print(json.dumps(exercise(sys.argv[1]),indent=2))
