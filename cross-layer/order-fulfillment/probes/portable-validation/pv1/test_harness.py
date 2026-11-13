import tempfile
from pathlib import Path
import unittest
import build
import mutations
import checks
import sys
sys.path.insert(0, str(build.CASE / "evolution"))

class HarnessTests(unittest.TestCase):
    def test_mutations_match_exactly_once(self):
        with tempfile.TemporaryDirectory() as directory:
            refs=build.materialize(Path(directory)/'refs')
            for condition in ('conventional','cohesive'):
                for name,(file,before,_,_,_) in mutations.mutations(condition).items():
                    self.assertEqual((refs/condition/'src/Fulfillment.Application'/file).read_text().count(before),1,(condition,name))
    def test_execution_failure_is_not_behavioral_detection(self):
        from harness import detected
        self.assertFalse(detected(1,{'kind':'unqualified'},'PV1-01','outcomes'))
        with self.assertRaises(RuntimeError):
            checks.check_items([{'index':0,'admission':{'status':202,'body':{}},'completion':{'status':500,'body':{'code':'ExecutionFailed'}}}], [{'status':202,'outcome':'OrderMissing'}])
    def test_wrong_assertion_is_not_detection(self):
        from harness import detected
        self.assertFalse(detected(1,{'kind':'behavioral','obligation':'PV1-01','assertion':'input decoding'},'PV1-01','outcomes'))

if __name__=='__main__':unittest.main()
