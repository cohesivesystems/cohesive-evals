"""Guard qualification against counting infrastructure or incidental failures."""
import tempfile
from pathlib import Path
import unittest
from build import materialize
from qualify import detected, mutations, EXPECTED_ASSERTIONS


class QualificationTests(unittest.TestCase):
    def test_only_named_behavioral_failure_counts(self):
        good={'kind':'behavioral','obligation':'E1-02','assertion':'limit enforcement'}
        self.assertTrue(detected(1,good,'E1-02','limit enforcement'))
        for code,failure in [(0,good),(1,None),(1,{}),
                             (1,{**good,'kind':'unqualified'}),
                             (1,{**good,'obligation':'E1-01'}),
                             (1,{**good,'assertion':'unrelated failure'})]:
            with self.subTest(code=code,failure=failure):
                self.assertFalse(detected(code,failure,'E1-02','limit enforcement'))

    def test_mutants_target_one_authored_anchor_each(self):
        with tempfile.TemporaryDirectory() as directory:
            refs=materialize(Path(directory)/'refs')
            for condition in ['conventional','cohesive']:
                self.assertEqual(set(mutations(condition)),set(EXPECTED_ASSERTIONS))
                for name,(file,before,after,obligation) in mutations(condition).items():
                    source=(refs/condition/'src/Fulfillment.Application'/file).read_text()
                    self.assertEqual(source.count(before),1,(condition,name))
                    self.assertNotEqual(before,after)
                    self.assertIn(obligation,['E1-01','E1-02','E1-03'])


if __name__=='__main__':unittest.main()
