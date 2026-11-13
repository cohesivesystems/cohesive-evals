#!/usr/bin/env python3
"""Ordinary public smoke checks for batch-examples.json and batch-seed.json."""
import argparse
import json
from pathlib import Path
import urllib.request

def exercise(url, output):
    items=json.loads(output.read_text())['items']
    assert len(items)==3
    assert [x['admission']['status'] for x in items]==[202,400,202]
    assert items[0]['admission']==items[2]['admission']
    assert items[0]['completion']==items[2]['completion']=={'status':200,'body':{'status':'Submitted','outcome':'ReservedAndSubmitted'}}
    assert 'completion' not in items[1]
    request=urllib.request.Request(url+'/fulfillment',data=json.dumps({'requestId':'example','orderId':'draft','sku':'stock','quantity':2}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request) as response:
        assert response.status==202 and json.load(response)==items[0]['admission']['body']
    with urllib.request.urlopen(url+'/inventory/stock') as response:
        assert json.load(response)['available']==3
    return 5

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(exercise(args.url,args.output),'public checks passed')
