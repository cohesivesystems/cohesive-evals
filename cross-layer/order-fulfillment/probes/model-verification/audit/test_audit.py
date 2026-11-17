"""The audit oracle must reject shared wrong results, not merely compare conditions."""
import copy
import json
from pathlib import Path
import unittest
import run

EVIDENCE=Path(__file__).resolve().parents[1]/'evidence'

class AuditTests(unittest.TestCase):
    def test_recorded_examples_match_independent_expectations(self):
        for condition in run.build.harness.CONDITIONS:
            run.validate_rows(json.loads((EVIDENCE/(condition+'.json')).read_text())['rows'])

    def test_same_wrong_result_in_both_conditions_is_not_success(self):
        for condition in run.build.harness.CONDITIONS:
            rows=json.loads((EVIDENCE/(condition+'.json')).read_text())['rows']
            rows[0]['Outcome']='InventoryQuarantined'
            with self.assertRaises(AssertionError):run.validate_rows(rows)

    def test_missing_cases_and_wrong_effects_fail(self):
        rows=json.loads((EVIDENCE/'conventional.json').read_text())['rows']
        with self.assertRaises(AssertionError):run.validate_rows(rows[:-1])
        wrong=copy.deepcopy(rows);wrong[5]['After']=10
        with self.assertRaises(AssertionError):run.validate_rows(wrong)

if __name__=='__main__':unittest.main()
