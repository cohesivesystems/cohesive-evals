import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import build

checks=build.load('ao1_test_checks',build.ROOT/'checks.py')
mutations=build.load('ao1_test_mutations',build.ROOT/'mutations.py')
diagnostics=build.load('ao1_test_diagnostics',build.ROOT/'diagnostics.py')
alias=build.load('ao1_test_alias',build.ROOT/'alias_witness.py')

class HarnessTests(unittest.TestCase):
    def test_deltas_and_mutation_anchors(self):
        with tempfile.TemporaryDirectory() as temp:
            refs=build.materialize(Path(temp)/'refs')
            pins=json.loads((build.ROOT/'shared-source-pins.json').read_text())
            build.harness.matching_artifacts(refs,[],pins)
            for condition in build.harness.CONDITIONS:
                app=refs/condition/'src/Fulfillment.Application'
                for name,(file,before,after,_,_) in mutations.mutations(condition).items():
                    self.assertNotEqual(before,after,name)
                    self.assertEqual((app/file).read_text().count(before),1,(condition,name))
                for name,(_,_,edits) in diagnostics.cases(condition).items():
                    for file,before,after in edits:
                        self.assertEqual((app/file).read_text().count(before),1,(condition,name))
                # Schema and source pins cannot silently waive a schema mismatch.
                for schema in ('schemas.json','seed.schema.json'):
                    self.assertIn('Archived',(refs/condition/schema).read_text())
            path=refs/'cohesive/schemas.json';path.write_text(path.read_text()+'\n')
            with self.assertRaises(AssertionError):build.harness.matching_artifacts(refs,[],pins)

    def test_alias_witness_anchors(self):
        with tempfile.TemporaryDirectory() as temp:
            for variant in (False,True):
                refs=build.materialize(Path(temp)/str(variant))
                for condition in build.harness.CONDITIONS:alias.prepare(refs/condition,condition,variant)

    def test_named_assertions_only(self):
        good=dict(kind='behavioral',obligation='AO1-02',assertion='archived compensation')
        self.assertTrue(build.harness.detected(1,good,'AO1-02','archived compensation'))
        for code,failure in [(0,good),(1,None),(1,{**good,'kind':'unqualified'}),
                             (1,{**good,'assertion':'archived fulfillment outcome'}),
                             (1,{**good,'obligation':'AO1-03'})]:
            self.assertFalse(build.harness.detected(code,failure,'AO1-02','archived compensation'))

    def test_server_failure_is_unqualified(self):
        world=SimpleNamespace(client=SimpleNamespace(request=lambda *args:(500,{'code':'ExecutionFailed'})))
        with self.assertRaises(RuntimeError):checks.Checks(world).call('GET','/anything')
        world.client.request=lambda *args:(409,{'code':'WrongCode'})
        with self.assertRaises(checks.BehavioralFailure):
            test=checks.Checks(world)
            test.check(test.call('POST','/submit')==(409,{'code':'OrderArchived'}),'01','archived direct submission','wrong code')
        for item in ({'index':0,'admission':{'status':202},'completion':{'status':500}},
                     {'index':0,'admission':{'status':500}}):
            world.client.request=lambda *args:(200,{'items':[item]})
            with self.assertRaises(RuntimeError):checks.Checks(world).items('batch',[{}],['OrderArchived'],'02','archived fulfillment outcome')
            # Conflict/replay checks also use call directly, so classification belongs there.
            with self.assertRaises(RuntimeError):checks.Checks(world).call('POST','/fulfillment/batch',[{}])

    def test_static_diagnostic_requires_matching_stage_and_error(self):
        line='FulfillmentBackend.cs(4,5): error CS1503: wrong type'
        for command,expected in [(['dotnet','build'],True),(['dotnet','restore'],False)]:
            error=subprocess.CalledProcessError(1,command)
            self.assertEqual(diagnostics.compile_detected(error,line,'error CS1503:'),expected)
        self.assertFalse(diagnostics.compile_detected(subprocess.TimeoutExpired(['dotnet','build'],1),line,'error CS1503:'))
        self.assertFalse(diagnostics.compile_detected(subprocess.CalledProcessError(1,['dotnet','build']),line,'error CS0029:'))
        diagnostic='System.ArgumentException: exact declaration mismatch'
        self.assertTrue(diagnostics.registration_detected(RuntimeError(('host readiness','host exited',-6)),diagnostic,diagnostic))
        for error in (RuntimeError('host readiness deadline'),subprocess.CalledProcessError(1,['dotnet','seed'])):
            self.assertFalse(diagnostics.registration_detected(error,diagnostic,diagnostic))

    def test_infrastructure_failure_report_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'run'
            with patch.object(diagnostics.runtime.pv1.harness,'run',side_effect=RuntimeError('injected Docker failure')):
                with self.assertRaisesRegex(RuntimeError,'injected Docker failure'):
                    with diagnostics.verification_run(out,'ao1-test',checks.BehavioralFailure):pass
            report=json.loads((out/'failure.json').read_text())
            self.assertEqual(report['kind'],'unqualified')
            self.assertIsNone(report['condition'])
            self.assertIn('injected Docker failure',report['detail'])

if __name__=='__main__':unittest.main()
