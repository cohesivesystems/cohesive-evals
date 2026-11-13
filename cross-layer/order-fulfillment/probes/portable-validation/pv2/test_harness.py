import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class HarnessTests(unittest.TestCase):
    def test_delta_and_mutation_anchors(self):
        build = load('test_pv2_build', 'build.py')
        mutations = load('test_pv2_mutations', 'mutations.py')
        with tempfile.TemporaryDirectory() as directory:
            parent = build.previous.materialize(Path(directory)/'parent')
            refs = build.materialize(Path(directory)/'refs')
            for condition in ('conventional','cohesive'):
                source = refs/condition/'src/Fulfillment.Application'
                changed = [p.name for p in source.glob('*.cs') if p.read_bytes() != (parent/condition/'src/Fulfillment.Application'/p.name).read_bytes()]
                self.assertEqual(changed, ['FulfillmentInput.cs'])
                for name,(file,before,_,_,_) in mutations.mutations(condition).items():
                    self.assertEqual((source/file).read_text().count(before),1,(condition,name))
            self.assertEqual((refs/'conventional/src/Fulfillment.Application/FulfillmentInput.cs').read_bytes(),
                             (refs/'cohesive/src/Fulfillment.Application/FulfillmentInput.cs').read_bytes())

if __name__ == '__main__':
    unittest.main()
