#!/usr/bin/env python3
"""Require named E2 behavioral failures from independently built application mutants."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from build import ROOT, CASE, materialize, build_tools


def mutations(condition):
    cases = {
        'lost-replay': ('OperationQueue.cs', 'Results.Json(previous.Admission, statusCode: 202)',
                        'Results.Conflict(new ErrorResponse("LostReplay"))', 'E2-03'),
    }
    if condition == 'conventional':
        cases.update({
            'cancel-submitted': ('Domain.cs', 'order.Status is OrderStatus.Draft or OrderStatus.Cancelled', 'true', 'E2-01'),
            'non-idempotent-cancel': ('Domain.cs', 'order.Status is OrderStatus.Draft or OrderStatus.Cancelled', 'order.Status == OrderStatus.Draft', 'E2-01'),
            'direct-submit-code': ('FulfillmentBackend.cs', 'SubmissionOutcome.OrderCancelled => Results.Conflict(new ErrorResponse("OrderCancelled"))',
                                   'SubmissionOutcome.OrderCancelled => Results.Conflict(new ErrorResponse("OrderNotDraft"))', 'E2-02'),
            'fulfillment-code': ('FulfillmentBackend.cs', 'submitted == SubmissionOutcome.OrderCancelled ? "OrderCancelled" : "OrderRejected"', '"OrderRejected"', 'E2-02'),
            'early-cancellation': ('FulfillmentBackend.cs', 'if (order is null) return Reject("OrderMissing");',
                                   'if (order is null) return Reject("OrderMissing");\n        if (order.Status == OrderStatus.Cancelled) return Reject("OrderCancelled");', 'E2-02'),
            'skipped-compensation': ('FulfillmentBackend.cs', 'await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");', '', 'E2-02'),
        })
    else:
        cases.update({
            'cancel-submitted': ('FulfillmentDomain.cs', 'order.Status == OrderStatus.Draft || order.Status == OrderStatus.Cancelled', 'true', 'E2-01'),
            'non-idempotent-cancel': ('FulfillmentDomain.cs', 'order.Status == OrderStatus.Draft || order.Status == OrderStatus.Cancelled', 'order.Status == OrderStatus.Draft', 'E2-01'),
            'direct-submit-code': ('FulfillmentBackend.cs', 'new ErrorResponse(code["orders.submit.".Length..])',
                                   'new ErrorResponse(code.EndsWith("OrderCancelled", StringComparison.Ordinal) ? "OrderNotDraft" : code["orders.submit.".Length..])', 'E2-02'),
            'fulfillment-code': ('FulfillmentDomain.cs', 'return new FulfillmentResult(FulfillmentStatus.Rejected, FulfillmentOutcome.OrderCancelled);',
                                 'return new FulfillmentResult(FulfillmentStatus.Rejected, FulfillmentOutcome.OrderRejected);', 'E2-02'),
            'early-cancellation': ('FulfillmentDomain.cs', 'var existing = await process.PointRead(domain.Reservations, input.OrderId);',
                                   'if (original.Entity.Status == OrderStatus.Cancelled)\n            return new FulfillmentResult(FulfillmentStatus.Rejected, FulfillmentOutcome.OrderCancelled);\n        var existing = await process.PointRead(domain.Reservations, input.OrderId);', 'E2-02'),
            'skipped-compensation': ('FulfillmentDomain.cs', 'await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));', '', 'E2-02'),
        })
    return cases


EXPECTED_ASSERTIONS = {
    'cancel-submitted': 'cancellation state table',
    'non-idempotent-cancel': 'idempotent cancellation',
    'direct-submit-code': 'direct submit outcome',
    'fulfillment-code': 'cancelled fulfillment',
    'early-cancellation': 'missing inventory before cancellation',
    'skipped-compensation': 'cancelled fulfillment',
    'lost-replay': 'retained admission',
}


def detected(result_code, failure, obligation, assertion):
    return (result_code != 0 and failure is not None and failure.get('kind') == 'behavioral'
            and failure.get('obligation') == obligation and failure.get('assertion') == assertion)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    fixtures=materialize(out/'references');records=[]
    for condition in ('conventional','cohesive'):
        folder=fixtures/condition
        for name,mutation in {'known-good':None,**mutations(condition)}.items():
            candidate=out/condition/name;candidate.mkdir(parents=True)
            original=None
            try:
                if mutation:
                    file,before,after,expected=mutation;path=folder/'src/Fulfillment.Application'/file
                    original=path.read_text()
                    assert original.count(before)==1,(condition,name,'mutation anchor drift')
                    path.write_text(original.replace(before,after))
                    (candidate/'mutation.json').write_text(json.dumps({'file':file,'before':before,'after':after,
                        'expectedObligation':expected,'originalSha256':hashlib.sha256(original.encode()).hexdigest()},indent=2)+'\n')
                with (candidate/'build.log').open('w') as log:build_tools.build_candidate(folder,log)
                manifest=build_tools.verify_build(folder)
                (candidate/'build-manifest.json').write_bytes((folder/'build-manifest.json').read_bytes())
                command=[sys.executable,'-B',str(ROOT/'verify.py'),'--fixtures',str(fixtures),'--condition',condition,
                         '--output',str(candidate/'verification')]
                if mutation:command+=['--e2-only']
                with (candidate/'verification.log').open('w') as log:
                    result=subprocess.run(command,stdout=log,stderr=log,timeout=600)
                assert build_tools.verify_build(folder)==manifest,'Build changed during mutant verification'
                failed=candidate/'verification/failure.json';failure=json.loads(failed.read_text()) if failed.exists() else None
                if mutation:
                    assert detected(result.returncode, failure, expected, EXPECTED_ASSERTIONS[name]), (condition,name,'not qualified',failure)
                else:
                    assert result.returncode==0 and (candidate/'verification/report.json').exists(),(condition,'known-good failed',failure)
                records.append({'condition':condition,'case':name,'passed':True,'obligation':failure['obligation'] if failure else None,
                                'assertion':failure['assertion'] if failure else None, 'buildManifestSha256':manifest})
                print(condition,name,'qualified',flush=True)
            finally:
                if original is not None:path.write_text(original)
    (out/'report.json').write_text(json.dumps({'passed':True,'cases':records},indent=2)+'\n')


if __name__=='__main__':main()
