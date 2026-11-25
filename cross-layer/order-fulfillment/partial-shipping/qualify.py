"""Qualify matched behavior across the entire finite domain and score frozen clean proposals."""
import argparse
from itertools import product
import json
import subprocess
from pathlib import Path

from fixture import APP, CONDITIONS, ROOT, call, compile_suite, fixtures, install_source

DOMAIN = [dict(Status=s, Hold=h, Remaining=r, Quantity=q)
          for s, h, r, q in product(('Draft', 'Submitted', 'Packed', 'Cancelled', 'Shipped'),
                                    (False, True), range(1, 5), range(-1, 6))]
BUDGET = 8


def expected(case):
    """Compute the independent public outcome for a single contract input."""
    remaining = case['Remaining']
    quantity = case['Quantity']
    accepted = case['Status'] == 'Packed' and not case['Hold'] and 1 <= quantity <= remaining
    after = remaining - quantity if accepted else remaining
    return dict(Accepted=accepted, Status='Shipped' if accepted and after == 0 else case['Status'],
                Id='order-A', Hold=case['Hold'], Remaining=after)


def replay(folder, cases):
    """Return indexed contract failures and retain the adapter's diagnostic on execution failure."""
    try:
        actual = call(folder, 'execute', cases)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f'{folder.name} execution failed: {error.stderr}') from error
    return [dict(input=c, expected=expected(c), actual=a) for c, a in zip(cases, actual, strict=True)
            if a != expected(c)]


def proposals(folder):
    """Freeze ordered clean proposals; reject instability, invalid types, duplicates and over-budget suites."""
    cases = call(folder, 'propose')
    if cases != call(folder, 'propose') or not isinstance(cases, list) or not 0 < len(cases) <= BUDGET:
        raise ValueError(f'{folder.name}: invalid or unstable proposal count')
    for case in cases:
        if case not in DOMAIN or any(type(case[key]) != type(value) for key, value in DOMAIN[0].items()):
            raise ValueError(f'Invalid proposal: {case}')
    if len({tuple(c[k] for k in DOMAIN[0]) for c in cases}) != len(cases):
        raise ValueError('Duplicate proposals')
    return cases


def qualify(output, preflight=False):
    """Build and witness each mutation independently; only reproducible contract mismatches earn credit."""
    folders = output / 'fixtures'
    fixtures(folders)
    controls = json.loads((ROOT / 'controls.json').read_text())
    signatures = {}
    report = {}
    for condition in CONDITIONS:
        folder = folders / condition
        cases = []
        if not preflight:
            receipts = json.loads((ROOT / 'sessions.json').read_text())
            install_source(ROOT / 'submissions' / f'{condition}.cs', folder / 'Suite/Cases.cs', receipts[condition])
            compile_suite(folder)
            cases = proposals(folder)
        record = report[condition] = dict(cases=cases, controls={})
        if replay(folder, DOMAIN):
            raise ValueError(f'{condition}: reference violates shipping contract')
        source = folder / APP / ('Domain.cs' if condition == 'conventional' else 'FulfillmentDomain.cs')
        original = source.read_text()
        for control in controls:
            name = control['id']
            before, after = control[condition]
            if original.count(before) != 1:
                raise ValueError(f'{condition}/{name}: mutation anchor drift')
            print(f'Qualifying {condition}/{name}', flush=True)
            try:
                source.write_text(original.replace(before, after))
                compile_suite(folder)
                wrong = replay(folder, DOMAIN)
                witness = next((m for m in wrong if m['input'] == control['witness']), None)
                if witness is None or wrong != signatures.setdefault(name, wrong):
                    raise ValueError(f'{condition}/{name}: unmatched behavior or missing pinned witness')
                found = replay(folder, cases) if cases else []
                if cases and found != replay(folder, cases):
                    raise ValueError(f'{condition}/{name}: inconsistent suite replay')
                record['controls'][name] = dict(witness=witness, mismatchingInputs=len(wrong), detections=found)
            finally:
                source.write_text(original)
    (output / 'results.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--preflight', action='store_true', help='Validate clean and paired mutated behavior before authoring')
    args = parser.parse_args()
    qualify(args.output.resolve(), args.preflight)
