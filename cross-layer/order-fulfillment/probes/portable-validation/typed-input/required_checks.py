"""Independent nonblank-policy checks supplement the unchanged PV2 expectations."""
from pathlib import Path
import build
import json
previous = build.load('typed_input_previous_checks', Path(__file__).resolve().parents[1] / 'pv2/length_checks.py')
BehavioralFailure = previous.BehavioralFailure
require = previous.require
fixture = previous.fixture

class Checks(previous.Checks):
    def run(self):
        result = super().run()
        before = self.world.facts()
        count = 0
        for mode in ('http', 'batch'):
            for field in ('requestId', 'orderId', 'sku'):
                for value in ('', None, ' ', '\t\r\n', '\u2003'):
                    identity = 'required-' + str(count)
                    request = previous.request(identity)
                    request[field] = value
                    # Assert the admission boundary before polling any erroneously admitted work.
                    if mode == 'http':
                        status, body = self.world.client.request('POST', '/fulfillment', request)
                        if status >= 500: raise RuntimeError(('required admission infrastructure failure', status, body))
                    else:
                        reply = self.world.send_batch(json.dumps([request]))
                        require(self.world.batch_status == 200, 'TI-01', 'required input', reply)
                        status = reply['items'][0]['admission']['status']
                        if status >= 500: raise RuntimeError(('required admission infrastructure failure', reply))
                    require(status == 400, 'TI-01', 'required input', (mode, field, value, status))
                    self.trace.append({'mode': mode, 'requiredField': field, 'value': value, 'status': status})
                    # Rejected input cannot retain identity or effects; valid retry is still admitted.
                    self.send(mode, [previous.request(identity)], [previous.admitted()], 'TI-01', 'required input')
                    count += 1
        self.facts(before, 'required preservation')
        return {**result, 'requiredInputCases': count}
