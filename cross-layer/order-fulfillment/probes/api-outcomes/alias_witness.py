#!/usr/bin/env python3
"""Paired declared-name/JSON-alias witness; keeps the actual typed-map reference intact."""
import argparse
import difflib
import json
from pathlib import Path
import subprocess
import sys
import build

def replace(path,before,after):
    text=path.read_text()
    if text.count(before)!=1:raise ValueError(('alias witness anchor',path,before))
    path.write_text(text.replace(before,after))

def prepare(folder,condition,alias):
    app=folder/'src/Fulfillment.Application'
    if condition=='cohesive':
        path=app/'FulfillmentDomain.cs'
        before='return new FulfillmentResult(FulfillmentStatus.Rejected, submitted.FulfillmentOutcome);'
        replace(path,before,'''if (submitted.Outcome == SubmissionOutcome.OrderArchived)
            return new FulfillmentResult(FulfillmentStatus.Rejected, FulfillmentOutcome.OrderArchived);
        return new FulfillmentResult(FulfillmentStatus.Rejected, submitted.FulfillmentOutcome == FulfillmentOutcome.OrderArchived
            ? FulfillmentOutcome.OrderRejected : submitted.FulfillmentOutcome);''')
        if alias:
            replace(path,'[JsonStringEnumMemberName("OrderArchived")] OrderArchived','[JsonStringEnumMemberName("OrderArchived")] Archived')
            replace(path,'SubmissionOutcome.OrderArchived, FulfillmentOutcome.OrderArchived','SubmissionOutcome.Archived, FulfillmentOutcome.OrderArchived')
            replace(path,'submitted.Outcome == SubmissionOutcome.OrderArchived','submitted.Outcome == SubmissionOutcome.Archived')
            replace(app/'FulfillmentBackend.cs','SubmissionOutcome.OrderArchived => "OrderArchived"','SubmissionOutcome.Archived => "OrderArchived"')
    else:
        path=app/'FulfillmentBackend.cs'
        replace(path,'return FulfillmentResults.FromSubmission(submitted);','''if (submitted == SubmissionOutcome.OrderArchived) return Reject("OrderArchived");
        return FulfillmentResults.FromSubmission(submitted);''')
        if alias:
            replace(app/'Domain.cs','Submitted, NotDraft, OrderCancelled, OrderArchived }',
                'Submitted, NotDraft, OrderCancelled, [System.Text.Json.Serialization.JsonStringEnumMemberName("OrderArchived")] Archived }')
            replace(app/'Domain.cs','OrderStatus.Archived => SubmissionOutcome.OrderArchived','OrderStatus.Archived => SubmissionOutcome.Archived')
            replace(path,'submitted == SubmissionOutcome.OrderArchived','submitted == SubmissionOutcome.Archived')
            replace(path,'SubmissionOutcome.OrderArchived => Results.Conflict','SubmissionOutcome.Archived => Results.Conflict')
            replace(app/'FulfillmentResults.cs','SubmissionOutcome.OrderArchived => "OrderArchived"','SubmissionOutcome.Archived => "OrderArchived"')

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    records=[]
    for alias in (False,True):
        variant='alias' if alias else 'declared-name-control'
        refs=build.materialize(output/variant/'references')
        for condition in build.harness.CONDITIONS:
            folder=refs/condition;out=output/variant/condition;out.mkdir()
            before={p:p.read_text() for p in (folder/'src/Fulfillment.Application').glob('*.cs')}
            prepare(folder,condition,alias)
            delta=''.join(''.join(difflib.unified_diff(text.splitlines(True),p.read_text().splitlines(True),fromfile='a/'+p.name,tofile='b/'+p.name)) for p,text in before.items())
            (out/'mutation.patch').write_text(delta)
            with (out/'build.log').open('w') as log: build.build_tools.build_candidate(folder,log)
            (out/'build-manifest.json').write_bytes((folder/'build-manifest.json').read_bytes())
            with (out/'verify.log').open('w') as log:
                result=subprocess.run([sys.executable,'-B',str(build.ROOT/'verify.py'),'--fixtures',str(refs),'--condition',condition,'--output',str(out/'verification')],stdout=log,stderr=log,timeout=300)
            failurepath=out/'verification/failure.json'
            failure=json.loads(failurepath.read_text()) if failurepath.exists() else None
            expected_failure=alias and condition=='cohesive'
            if expected_failure:
                passed=build.harness.detected(result.returncode,failure,'AO1-02','archived fulfillment outcome')
            else:
                report=out/'verification/report.json'
                passed=result.returncode==0 and report.exists() and json.loads(report.read_text()).get('passed') is True
            records.append(dict(condition=condition,variant=variant,passed=passed,expectedBehavioralFailure=expected_failure,
                failure=failure,buildManifestSha256=build.build_tools.verify_build(folder)))
            (output/'report.json').write_text(json.dumps({'passed':all(x['passed'] for x in records),'complete':len(records)==4,'cases':records},indent=2)+'\n')
            if not passed:raise RuntimeError(('alias witness unexpected result',condition,variant,failure))
            print(condition,variant,'observed',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output.resolve())
