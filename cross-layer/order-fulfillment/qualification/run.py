#!/usr/bin/env python3
"""Build isolated application mutants and require behavioral assertion failures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP = Path('src/Fulfillment.Application')


def mutations(condition):
    common = {
        'lost-replay': ('OperationQueue.cs', 'Results.Json(previous.Admission, statusCode: 202)',
                        'Results.Conflict(new ErrorResponse("LostReplay"))', 'admission replay'),
        'identity-conflict-accepted': ('OperationQueue.cs', ': Results.Conflict(new ErrorResponse("RequestIdentityConflict"));',
                                     ': Results.Json(previous.Admission, statusCode: 202);', 'identity conflict'),
    }
    if condition == 'conventional':
        domain = 'Domain.cs'
        backend = 'FulfillmentBackend.cs'
        create = 'await store.CreateReservation(new(request.OrderId, request.OrderId, request.Sku, request.Quantity), operationId + "/reservation");'
        common.update({
            'extra-stock-decrement': (domain, 'item.Available - quantity', 'item.Available - quantity - 1', 'stock conservation'),
            'skipped-compensation': (backend, 'await store.Stock(request.Sku, request.Quantity, true, operationId + "/release");', '', 'stock conservation'),
            'missing-reservation': (backend, create, '', 'stock conservation'),
            'duplicate-reservation': (backend, create, create+'\n            await store.CreateReservation(new(request.OrderId + "-duplicate", request.OrderId, request.Sku, request.Quantity), operationId + "/duplicate");', 'duplicate reservation per order'),
        })
    else:
        domain = 'FulfillmentDomain.cs'
        create = 'await process.Transition(domain.ReservationTransitions.Create, input.OrderId,\n                new Reservation(input.OrderId, stock.Entity.Partition, input.OrderId, input.Sku, input.Quantity));'
        common.update({
            'extra-stock-decrement': (domain, 'item.Available - input.Quantity', 'item.Available - input.Quantity - 1', 'stock conservation'),
            'skipped-compensation': (domain, 'await process.Transition(domain.InventoryTransitions.Release, input.Sku, new StockQuantity(input.Quantity));', '', 'stock conservation'),
            'missing-reservation': (domain, create, '', 'stock conservation'),
            'duplicate-reservation': (domain, create, create+'\n            await process.Transition(domain.ReservationTransitions.Create, input.OrderId + "-duplicate",\n                new Reservation(input.OrderId + "-duplicate", stock.Entity.Partition, input.OrderId, input.Sku, input.Quantity));', 'duplicate reservation per order'),
        })
    return common


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/qualification')
    args = parser.parse_args()
    args.output = args.output.resolve(); args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'report.json').unlink(missing_ok=True)
    records = []
    with tempfile.TemporaryDirectory(prefix='order-mutants-') as temporary:
        conditions = Path(temporary)/'conditions'
        shutil.copytree(ROOT/'conditions', conditions, ignore=shutil.ignore_patterns('bin','obj','__pycache__'))
        for condition in ['conventional', 'cohesive']:
            folder = conditions/condition
            cases = {'known-good': None, **mutations(condition)}
            for name, mutation in cases.items():
                output = args.output/condition/name; output.mkdir(parents=True, exist_ok=True)
                original = None
                try:
                    if mutation:
                        file, before, after, expected = mutation
                        path = folder/APP/file; original = path.read_text()
                        assert original.count(before) == 1, (condition,name,'mutation anchor changed')
                        path.write_text(original.replace(before, after))
                        (output/'mutation.json').write_text(json.dumps({'file':str(APP/file),'before':before,'after':after,
                            'originalSha256':hashlib.sha256(original.encode()).hexdigest()},indent=2)+'\n')
                    with (output/'build.log').open('w') as log:
                        subprocess.run(['dotnet','restore','--locked-mode'],cwd=folder,stdout=log,stderr=log,check=True,timeout=120)
                        subprocess.run(['dotnet','build','--no-restore','-m:1','-nr:false'],cwd=folder,stdout=log,stderr=log,check=True,timeout=120)
                    with (output/'verification.log').open('w') as log:
                        result = subprocess.run([sys.executable,'-B',str(ROOT/'verification/verify.py'),
                            '--fixtures',str(conditions),'--condition',condition,'--suite','invariants','--output',str(output)],
                            stdout=log,stderr=log,timeout=240)
                    failure_path = output/'assertion-failure.json'
                    failure = json.loads(failure_path.read_text()) if failure_path.exists() else None
                    if mutation:
                        assert result.returncode != 0 and failure and expected in failure['error'], (condition,name,'not detected by expected behavioral assertion',failure)
                    else:
                        assert result.returncode == 0 and (output/'report.json').exists(), (condition,'known-good failed')
                    records.append({'condition':condition,'case':name,'passed':True,'assertion':failure})
                    print(condition, name, 'qualified', flush=True)
                finally:
                    if original is not None: path.write_text(original)
    report = {'passed':True,'cases':records,'limitations':['G0 sequential invariants only','No crash or concurrency qualification','Not full cumulative oracle qualification']}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__': main()
