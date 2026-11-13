"""Shared profile selection and exact-parent snapshot regression checks."""
import json
from pathlib import Path
import tempfile
import unittest
import harness
from unittest.mock import patch
from harness import profile, selected_profiles, detected, adapt_inventory, inventory_fields, newer_inventory_fields
from snapshot import apply_delta


class SharedHarnessTests(unittest.TestCase):
    def test_cumulative_and_targeted_selection(self):
        self.assertEqual([p['name'] for p in selected_profiles('e1')], ['e1'])
        self.assertEqual([p['name'] for p in selected_profiles('e2')], ['e1', 'e2'])
        self.assertEqual([p['name'] for p in selected_profiles('e2', True)], ['e2'])
        self.assertEqual([p['name'] for p in selected_profiles('e3')], ['e1', 'e2', 'e3'])
        self.assertEqual([p['name'] for p in selected_profiles('e3', True)], ['e3'])

    def test_only_intended_behavioral_failure_earns_credit(self):
        good = {'kind': 'behavioral', 'obligation': 'E2-02', 'assertion': 'cancelled fulfillment'}
        self.assertTrue(detected(1, good, 'E2-02', 'cancelled fulfillment'))
        for status, failure in [(0, good), (1, None), (1, {}),
                                (1, {**good, 'kind': 'unqualified'}),
                                (1, {**good, 'obligation': 'E1-02'}),
                                (1, {**good, 'assertion': 'different failure'})]:
            self.assertFalse(detected(status, failure, 'E2-02', 'cancelled fulfillment'))

    def test_prior_inventory_checks_new_field_before_adapting(self):
        value = {'sku': 'prior', 'available': 2, 'maxPerOrder': 3, 'quarantined': False}
        hidden = newer_inventory_fields('e3', 'e2')
        self.assertEqual(adapt_inventory(value, hidden), {'sku': 'prior', 'available': 2, 'maxPerOrder': 3})
        self.assertIn('quarantined', value)
        for invalid in ({**value, 'quarantined': True}, {**value, 'quarantined': 0},
                        {k: v for k, v in value.items() if k != 'quarantined'}):
            with self.assertRaises(AssertionError):
                adapt_inventory(invalid, hidden)

    def test_field_projection_works_for_new_profile_declarations(self):
        self.assertEqual(set(inventory_fields('e1')), {'maxPerOrder'})
        self.assertEqual(inventory_fields('e2'), inventory_fields('e1'))
        value = {'sku': 'legacy', 'available': 2, 'maxPerOrder': 2147483647, 'quarantined': False}
        self.assertEqual(adapt_inventory(value, newer_inventory_fields('e3')), {'sku': 'legacy', 'available': 2})
        for wrong in (None, 0, True, 2147483647.0):
            with self.assertRaises(AssertionError):
                adapt_inventory({**value, 'maxPerOrder': wrong}, newer_inventory_fields('e3'))
        nullable = {'note': {'column': 'note', 'neutral': None}}
        self.assertEqual(adapt_inventory({**value, 'note': None}, nullable), value)
        with self.assertRaises(AssertionError):
            adapt_inventory(value, nullable)
        addition = {'future': {'inventoryFields': {'tagged': {'column': 'tagged', 'neutral': False}}}}
        with patch.dict(harness.PROFILE_CONFIG, addition), patch.object(harness, 'GENERATIONS', (*harness.GENERATIONS, 'future')):
            hidden = newer_inventory_fields('future', 'e3')
            self.assertEqual(adapt_inventory({**value, 'tagged': False}, hidden), value)
            with self.assertRaises(AssertionError):
                adapt_inventory({**value, 'tagged': True}, hidden)

    def test_all_generation_mutations_have_one_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            for generation in ('e1', 'e2', 'e3'):
                p = profile(generation)
                refs = p['build'].materialize(Path(directory) / generation)
                for condition in ('conventional', 'cohesive'):
                    cases = p['mutations'].mutations(condition)
                    self.assertEqual(set(cases), set(p['mutations'].EXPECTED_ASSERTIONS))
                    for name, (file, before, after, _) in cases.items():
                        source = (refs / condition / 'src/Fulfillment.Application' / file).read_text()
                        self.assertEqual(source.count(before), 1, (generation, condition, name))
                        self.assertNotEqual(before, after)

    def test_delta_rejects_parent_and_output_drift_without_writing_parent(self):
        p = profile('e2')
        root = Path(__file__).resolve().parent / 'e2/reference'
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            refs = p['build'].previous.materialize(directory / 'g1')
            folder = refs / 'conventional'
            source = folder / 'src/Fulfillment.Application/Domain.cs'
            original = source.read_bytes()
            source.write_bytes(original + b'\n// drift\n')
            with self.assertRaisesRegex(ValueError, 'Parent snapshot drift'):
                apply_delta(folder, root / 'conventional.patch', root / 'conventional.json')
            self.assertTrue(source.read_bytes().endswith(b'// drift\n'))
            source.write_bytes(original)
            hashes = json.loads((root / 'conventional.json').read_text())
            hashes['src/Fulfillment.Application/Domain.cs']['after'] = 'wrong'
            altered = directory / 'incorrect-output.json'
            altered.write_text(json.dumps(hashes))
            with self.assertRaisesRegex(ValueError, 'Delta output drift'):
                apply_delta(folder, root / 'conventional.patch', altered)
            self.assertEqual(source.read_bytes(), original)
            apply_delta(folder, root / 'conventional.patch', root / 'conventional.json')
            self.assertIn(b'OrderCancelled', source.read_bytes())


if __name__ == '__main__':
    unittest.main()
