#!/usr/bin/env python3
"""Require named E1 behavioral failures from independently built application mutants."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from build import ROOT, CASE, materialize, build_tools


def mutations(condition):
    cases={
        'wrong-default':('Contracts.cs','int MaxPerOrder = int.MaxValue','int MaxPerOrder = 1','E1-01'),
        'lost-replay':('OperationQueue.cs','Results.Json(previous.Admission, statusCode: 202)',
                       'Results.Conflict(new ErrorResponse("LostReplay"))','E1-03')}
    if condition=='conventional':
        cases.update({
            'missing-limit':('Domain.cs','quantity > item.MaxPerOrder','false','E1-02'),
            'off-by-one':('Domain.cs','quantity > item.MaxPerOrder','quantity >= item.MaxPerOrder','E1-02'),
            'wrong-precedence':('Domain.cs','quantity > item.MaxPerOrder','quantity > item.MaxPerOrder && quantity <= item.Available','E1-02'),
            'configuration-changes-stock':('OrderStore.cs','SET max_per_order=$2 WHERE','SET max_per_order=$2, available=0 WHERE','E1-01'),
            'skipped-compensation':('FulfillmentBackend.cs','await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");','','E1-02')})
    else:
        cases.update({
            'missing-limit':('FulfillmentDomain.cs','input.Quantity <= item.MaxPerOrder','true','E1-02'),
            'off-by-one':('FulfillmentDomain.cs','input.Quantity <= item.MaxPerOrder','input.Quantity < item.MaxPerOrder','E1-02'),
            'wrong-precedence':('FulfillmentDomain.cs','input.Quantity <= item.MaxPerOrder','input.Quantity <= item.MaxPerOrder || input.Quantity > item.Available','E1-02'),
            'configuration-changes-stock':('FulfillmentDomain.cs','.Set(new("limit/update"), item => item.MaxPerOrder, (_, input) => input.MaxPerOrder)',
                  '.Set(new("limit/update"), item => item.MaxPerOrder, (_, input) => input.MaxPerOrder)\n                .Set(item => item.Available, 0)','E1-01'),
            'skipped-compensation':('FulfillmentDomain.cs','await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));','','E1-02')})
    return cases


EXPECTED_ASSERTIONS = {
    'wrong-default':'seed/default/read', 'lost-replay':'retained admission',
    'missing-limit':'limit enforcement', 'off-by-one':'inclusive boundary',
    'wrong-precedence':'limit before shortage', 'configuration-changes-stock':'integral input',
    'skipped-compensation':'lifecycle rejection preserves stock'}


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
                if mutation:command+=['--e1-only']
                with (candidate/'verification.log').open('w') as log:
                    result=subprocess.run(command,stdout=log,stderr=log,timeout=240)
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
