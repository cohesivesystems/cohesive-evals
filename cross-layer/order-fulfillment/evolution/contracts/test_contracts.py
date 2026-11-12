"""Contract qualification only: schema examples, cumulative shapes and isolation."""
import json
from pathlib import Path
import tempfile
import unittest
from jsonschema import Draft202012Validator
from bundle import PROFILES, ROOT, baseline, documents, emit


def validator(document, name=''):
    schema = dict(document)
    if name:
        schema['$ref'] = '#/$defs/'+name
    return Draft202012Validator(schema)


class ContractTests(unittest.TestCase):
    def test_public_examples_for_every_profile(self):
        count = 0
        for checkpoint, probe in PROFILES:
            with self.subTest(checkpoint=checkpoint, probe=probe):
                bundle = documents(checkpoint, probe)
                schemas = {name: json.loads(bundle[name]) for name in ('schemas.json', 'seed.schema.json')}
                for schema in schemas.values():
                    Draft202012Validator.check_schema(schema)
                for example in json.loads(bundle['contract-examples.json']):
                    check = validator(schemas[example['document']], example['schema'])
                    for value in example['valid']:
                        check.validate(value)
                        count += 1
                    for value in example['invalid']:
                        self.assertFalse(check.is_valid(value), (checkpoint, probe, example['schema'], value))
                        count += 1
        self.assertGreater(count, 200)

    def test_cumulative_shapes_and_seed_defaults(self):
        for checkpoint, probe in PROFILES:
            with self.subTest(checkpoint=checkpoint, probe=probe):
                depth = int(checkpoint[1])
                bundle = documents(checkpoint, probe)
                wire = json.loads(bundle['schemas.json'])
                seed = json.loads(bundle['seed.schema.json'])
                statuses = ['Draft', 'Submitted'] + (['Cancelled'] if depth >= 2 else []) + (['OnHold'] if probe == 'H' else [])
                for status in ['Draft', 'Submitted', 'Cancelled', 'OnHold', 'Canceled']:
                    summary = {'id': 'o', 'status': status}
                    if probe == 'L':
                        summary['reviewMarked'] = False
                    self.assertEqual(validator(wire, 'OrderSummary').is_valid(summary), status in statuses)
                    self.assertEqual(validator(wire, 'OrderDetails').is_valid({**summary, 'reservations': []}), status in statuses)
                inv = {'sku': 's', 'available': 10}
                if depth >= 1:
                    inv['maxPerOrder'] = 2
                    self.assertEqual(seed['$defs']['Inventory']['properties']['maxPerOrder']['default'], 2147483647)
                if depth >= 3:
                    inv['quarantined'] = False
                    self.assertIs(seed['$defs']['Inventory']['properties']['quarantined']['default'], False)
                validator(wire, 'Inventory').validate(inv)
                for required in set(inv) - {'sku', 'available'}:
                    self.assertFalse(validator(wire, 'Inventory').is_valid({k:v for k,v in inv.items() if k != required}))
                seed_data = {'orders': [{'id':'o','status':'Draft'}], 'inventory':[{'sku':'s','available':10}], 'reservations':[]}
                validator(seed).validate(seed_data)
                self.assertEqual(seed_data['inventory'][0], {'sku':'s','available':10})
                for field, value, allowed in [('maxPerOrder', 2, depth>=1), ('quarantined', False, depth>=3)]:
                    seeded = {**seed_data, 'inventory':[{**seed_data['inventory'][0], field:value}]}
                    self.assertEqual(validator(seed).is_valid(seeded), allowed)
                if probe == 'L':
                    self.assertEqual(seed['properties']['reviews']['default'], [])
                else:
                    self.assertFalse(validator(seed).is_valid({**seed_data, 'reviews':[]}))

    def test_inactive_outcomes_and_probe_material_absent(self):
        tokens = {'E1': ['maxPerOrder', 'QuantityLimitExceeded'], 'E2':['Cancelled','OrderNotCancellable'],
                  'E3':['quarantined','InventoryQuarantined'], 'H':['OnHold','OrderNotHoldable'],
                  'L':['reviewMarked','mark-reviewed']}
        for checkpoint, probe in PROFILES:
            depth = int(checkpoint[1])
            bundle = documents(checkpoint, probe)
            all_text = '\n'.join(bundle.values())
            active = [f'E{i}' for i in range(1,depth+1)] + ([probe] if probe else [])
            for feature, words in tokens.items():
                for word in words:
                    if feature not in active:
                        self.assertNotIn(word, all_text, (checkpoint, probe, word))
            wire = json.loads(bundle['schemas.json'])
            for outcome, enabled in [('QuantityLimitExceeded',depth>=1),('OrderCancelled',depth>=2),
                                     ('InventoryQuarantined',depth>=3),('OrderOnHold',probe=='H')]:
                self.assertEqual(validator(wire, 'Completion').is_valid({'status':'Rejected','outcome':outcome}), enabled)
            for forbidden in ['COH-', 'test-matrix', 'LSM-', 'hidden check', 'other condition']:
                self.assertNotIn(forbidden, all_text)
        for probe in ['H','L']:
            text = (ROOT/'supplements'/f'{probe}.md').read_text()
            self.assertIn(text, documents('G0',probe)['CONTRACT.md'])
            self.assertIn(text, documents('G3',probe)['CONTRACT.md'])

    def test_current_read_shape_and_limits(self):
        for checkpoint, probe in PROFILES:
            wire = json.loads(documents(checkpoint,probe)['schemas.json'])
            row = {'id':'r','sku':'s','quantity':1,'availableStock':1}
            details = {'id':'o','status':'Draft','reservations':[row]*1000}
            if probe == 'L': details['reviewMarked'] = True
            validator(wire,'OrderDetails').validate(details)
            self.assertFalse(validator(wire,'OrderDetails').is_valid({**details,'reservations':[row]*1001}))
            availability = {'reservationId':'r','sku':'s','quantity':1,'availableStock':1}
            validator(wire,'AvailabilityResponse').validate([availability]*1000)
            self.assertFalse(validator(wire,'AvailabilityResponse').is_valid([availability]*1001))
            self.assertNotIn('reviewMarked', wire['$defs']['Availability']['properties'])

    def test_safe_deterministic_export(self):
        # Baseline inputs must match across conditions before any bundle is emitted.
        baseline('CONTRACT.md'); baseline('schemas.json')
        with tempfile.TemporaryDirectory() as temp:
            for checkpoint,probe in PROFILES:
                a=Path(temp)/f'{checkpoint}-{probe}-a'; b=Path(temp)/f'{checkpoint}-{probe}-b'
                emit(checkpoint,probe,a); emit(checkpoint,probe,b)
                self.assertEqual({p.name for p in a.iterdir()},
                                 {'CONTRACT.md','schemas.json','seed.schema.json','contract-examples.json'})
                for p in a.iterdir(): self.assertEqual(p.read_bytes(), (b/p.name).read_bytes())
                with self.assertRaises(FileExistsError): emit(checkpoint,probe,a)
            for checkpoint,probe in [('G1','H'),('G2','L'),('G3','H+L')]:
                output=Path(temp)/f'bad-{checkpoint}-{probe}'
                with self.assertRaises(ValueError): emit(checkpoint,probe,output)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
