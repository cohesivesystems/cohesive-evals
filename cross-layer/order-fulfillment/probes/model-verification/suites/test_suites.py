import copy
import json
from pathlib import Path
import unittest
import generate
import oracle

MODEL=json.loads((Path(__file__).resolve().parents[1]/'evidence/transition.json').read_text())

class SuiteTests(unittest.TestCase):
    def test_matched_cases_and_every_guard_accounted_for(self):
        ordinary=generate.generate('conventional','original')
        model=generate.generate('cohesive','original',MODEL)
        self.assertEqual(ordinary['cases'],model['cases'])
        self.assertEqual(len(model['generationCoverage']),len(MODEL['definition']['preconditions']))
        self.assertEqual({c['Quantity'] for c in model['cases']} & {-2147483648,2147483647}, {-2147483648,2147483647})

    def test_unsupported_is_not_silently_dropped(self):
        model=copy.deepcopy(MODEL)
        model['definition']['preconditions'][0]['predicate']={'$expr':'function','function':'unsupported'}
        with self.assertRaises(generate.Unsupported):generate.generate('cohesive','original',model)

    def test_generated_expected_results_are_not_from_model(self):
        model=copy.deepcopy(MODEL)
        model['definition']['preconditions']=[]
        suite=generate.generate('cohesive','original',model)
        zero=next(c for c in suite['cases'] if c['Quantity']==0)
        self.assertEqual(oracle.expected(zero,'original'),'InvalidQuantity')
        answer=dict(Name=zero['Name'],Outcome='Reserved',FulfillmentOutcome='ReservedAndSubmitted',
                    After=dict(Sku=zero['Sku'],Available=zero['Available'],MaxPerOrder=zero['MaxPerOrder'],Quarantined=zero['Quarantined']),ScopePreserved=True)
        with self.assertRaises(oracle.BehavioralFailure):oracle.check([zero],[answer],'original')

    def test_precedence_revision_and_nonpositive_preservation(self):
        c=dict(Quantity=2,Available=0,MaxPerOrder=1,Quarantined=True)
        self.assertEqual(oracle.expected(c,'original'),'InventoryQuarantined')
        self.assertEqual(oracle.expected(c,'revised'),'QuantityLimitExceeded')
        for version in ('original','revised'):
            self.assertEqual(oracle.expected({**c,'Quantity':0},version),'InvalidQuantity')

    def test_output_identity_and_effects_are_independent_obligations(self):
        c=dict(Name='x',Sku='stock',Available=10,MaxPerOrder=4,Quarantined=False,Quantity=2)
        r=dict(Name='x',Outcome='Reserved',FulfillmentOutcome='ReservedAndSubmitted',After=dict(Sku='stock',Available=8,MaxPerOrder=4,Quarantined=False),ScopePreserved=True)
        self.assertEqual(oracle.check([c],[r],'original')['accepted'],1)
        for change in ({'Name':'other'},{'After':{**r['After'],'Available':10}},{'FulfillmentOutcome':'OrderRejected'},{'ScopePreserved':False}):
            with self.assertRaises(oracle.BehavioralFailure):oracle.check([c],[{**r,**change}],'original')

if __name__=='__main__':unittest.main()
