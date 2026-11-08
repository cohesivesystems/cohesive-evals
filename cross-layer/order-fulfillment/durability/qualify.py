#!/usr/bin/env python3
"""Require running durable application defects to fail named recovery obligations."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'qualification'))
from run import mutations
from build import reference_fingerprint, build_candidate, verify_build


def main():
    output=ROOT.parent/'artifacts/durability-qualification';output.mkdir(parents=True,exist_ok=True)
    (output/'report.json').unlink(missing_ok=True)
    known_good=json.loads((ROOT.parent/'artifacts/durability/report.json').read_text())
    assert known_good['passed'] and len(known_good['cases'])==20, 'Run full known-good recovery verification first'
    for condition in ['conventional','cohesive']:
        assert known_good['referenceFingerprints'][condition] == reference_fingerprint(ROOT.parent/'artifacts/durable-reference'/condition), 'Reference changed since known-good qualification'
        assert known_good['buildManifests'][condition] == verify_build(ROOT.parent/'artifacts/durable-reference'/condition)
    records=[]
    with tempfile.TemporaryDirectory(prefix='order-durable-mutants-') as temp:
        references=Path(temp)/'references'
        shutil.copytree(ROOT.parent/'artifacts/durable-reference',references,ignore=shutil.ignore_patterns('bin','obj'))
        for condition in ['conventional','cohesive']:
            app=references/condition/'src/Fulfillment.Application'
            queue=app/'OperationQueue.cs'
            cases={
                'lost-admission-on-restart': ('OperationQueue.cs','await command.ExecuteNonQueryAsync();',
                    'await command.ExecuteNonQueryAsync();\n        await using var lose = database.CreateCommand("TRUNCATE durable_admissions");\n        await lose.ExecuteNonQueryAsync();','before-dispatch',False,'original result lookup'),
                'resume-only-on-post': ('OperationQueue.cs','static readonly JsonSerializerOptions Json',
                    'bool postSeen;\n    static readonly JsonSerializerOptions Json','before-dispatch',False,'Deadline exceeded: recovery completion'),
                'terminal-failure-pending': ('OperationQueue.cs','if (state?.RuntimeStatus is OrchestrationRuntimeStatus.Completed or OrchestrationRuntimeStatus.Failed or OrchestrationRuntimeStatus.Terminated)',
                    'if (state?.RuntimeStatus is OrchestrationRuntimeStatus.Completed)','terminal-failure',False,'Deadline exceeded: recovery completion'),
            }
            for name,expected in [('missing-reservation','reservation cardinality'),('skipped-compensation','stock after recovery'),('duplicate-reservation','reservation cardinality')]:
                file,before,after,_=mutations(condition)[name]
                if condition=='conventional':
                    file='FulfillmentWorkflow.cs'
                    if name=='missing-reservation': before='await Activities.CreateReservation(context, work);';after=''
                    elif name=='skipped-compensation':before='await Activities.Release(context, work);';after=''
                    else:
                        before='await new OrderStore(database).CreateReservation(new(r.OrderId,r.OrderId,r.Sku,r.Quantity),work.OperationId+"/reservation")'
                        after='await Duplicate(new OrderStore(database),r,work.OperationId+"/reservation")'
                cases[name]=(file,before,after,'after-reserve',name=='skipped-compensation',expected)
            for name,(file,before,after,point,reject,expected) in cases.items():
                path=app/file;original=path.read_text();assert original.count(before)==1,(name,'anchor')
                mutated=original.replace(before,after)
                if condition=='conventional' and name=='duplicate-reservation':
                    anchor='public sealed class CreateReservation(NpgsqlDataSource database) : TaskActivity<Work, bool>\n{'
                    mutated=mutated.replace(anchor,anchor+'''\n    static async Task<bool> Duplicate(OrderStore store, FulfillmentRequest r, string key)
    {
        await store.CreateReservation(new(r.OrderId,r.OrderId,r.Sku,r.Quantity),key);
        return await store.CreateReservation(new(r.OrderId+"-extra",r.OrderId,r.Sku,r.Quantity),key+"-extra");
    }
''')
                if name=='resume-only-on-post':
                    mutated=mutated.replace('public async Task<IResult> Admit(FulfillmentRequest request)\n    {', 'public async Task<IResult> Admit(FulfillmentRequest request)\n    {\n        postSeen = true;')
                    mutated=mutated.replace('var state = await client.GetInstanceAsync', 'if (!postSeen) { await Task.Delay(100, stoppingToken); continue; }\n                    var state = await client.GetInstanceAsync')
                path.write_text(mutated)
                evidence=output/condition/name;evidence.mkdir(parents=True,exist_ok=True)
                (evidence/'mutation.json').write_text(json.dumps({'file':file,'before':before,'after':after},indent=2)+'\n')
                try:
                    with (evidence/'build.log').open('w') as log:
                        build_candidate(references/condition, log)
                    command=[sys.executable,'-B',str(ROOT/'verify.py'),'--references',str(references),'--condition',condition,'--point',point,'--output',str(evidence)]
                    if reject:command.append('--reject')
                    with (evidence/'verification.log').open('w') as log:
                        result=subprocess.run(command,stdout=log,stderr=log,timeout=240)
                    failure=evidence/'assertion-failure.json'
                    detail=json.loads(failure.read_text()) if failure.exists() else None
                    assert result.returncode!=0 and detail and expected in detail['error'],(condition,name,'incorrect failure',detail)
                    records.append({'condition':condition,'mutation':name,'assertion':detail['error'],'passed':True})
                    print(condition,name,'qualified',flush=True)
                finally:path.write_text(original)
    (output/'report.json').write_text(json.dumps({'passed':True,'cases':records},indent=2)+'\n')

if __name__=='__main__':main()
