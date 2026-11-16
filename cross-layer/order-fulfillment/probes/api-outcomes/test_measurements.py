import copy
import json
from pathlib import Path
import tempfile
import unittest
import measure

class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.report=json.loads((measure.ROOT/'evidence/qualification.json').read_text())

    def test_unmatched_fault_is_not_a_paired_win(self):
        paired,unpaired=measure.behavioral_pairs(self.report)
        self.assertEqual(len(paired),14)
        self.assertEqual(unpaired,{'conventional':['wrong-http-category'],'cohesive':[]})
        row=next(x for x in self.report['cases'] if x['case']=='constant-input' and x['condition']=='cohesive')
        row['failure']['assertion']='unrelated'
        with self.assertRaises(ValueError):measure.behavioral_pairs(self.report)

    def test_inconclusive_failures_and_missing_controls_are_not_detections(self):
        for kind in ('unqualified',None):
            report=copy.deepcopy(self.report)
            report['cases'][1]['failure']['kind']=kind
            with self.assertRaises(ValueError):measure.behavioral_pairs(report)
        report=copy.deepcopy(self.report)
        report['cases']=[r for r in report['cases'] if not (r['condition']=='cohesive' and r['case']=='known-good')]
        with self.assertRaises(ValueError):measure.behavioral_pairs(report)

    def test_summary_is_reproducible_and_rejects_evidence_drift(self):
        expected=json.loads((measure.ROOT/'measurements.json').read_text())
        self.assertEqual(measure.measure(),expected)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'evidence').mkdir()
            (root/'evidence.json').write_bytes((measure.ROOT/'evidence.json').read_bytes())
            (root/'evidence/qualification.json').write_text('{"passed":true}')
            with self.assertRaisesRegex(ValueError,'Evidence drift'):measure.measure(root)

if __name__=='__main__':unittest.main()
