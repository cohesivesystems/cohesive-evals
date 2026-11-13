#!/usr/bin/env python3
"""Public PV2 boundary examples against an ordinary seeded host."""
import argparse
import json
import urllib.error
import urllib.request

def exercise(url):
    def post(route, body):
        request = urllib.request.Request(url+route, data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    def intent(identity):
        return dict(requestId=identity, orderId='pv2-visible-missing', sku='stock', quantity=1)
    assert post('/fulfillment', intent('v'*64))[0] == 202
    assert post('/fulfillment', intent('v'*65))[0] == 400
    status, reply = post('/fulfillment/batch', [intent('😀'*32), intent('😀'*32+'x')])
    assert status == 200
    assert [item['admission']['status'] for item in reply['items']] == [202,400]
    assert reply['items'][0]['completion'] == {'status':200,'body':{'status':'Rejected','outcome':'OrderMissing'}}
    return 5

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    print(exercise(parser.parse_args().url), 'public checks passed')
