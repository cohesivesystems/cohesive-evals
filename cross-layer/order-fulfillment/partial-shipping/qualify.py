"""Qualify matched behavior across the entire finite domain and score frozen clean proposals."""
import argparse
import hashlib
from itertools import product
import json
import shutil
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
    if cases != call(folder, 'propose'):
        raise ValueError(f'{folder.name}: unstable proposals')
    return validate_cases(cases)


def validate_cases(cases):
    """Enforce the common domain and suite budget for submitted and SDK-selected proposals."""
    if not isinstance(cases, list) or not 0 < len(cases) <= BUDGET:
        raise ValueError('Invalid proposal count')
    for case in cases:
        if case not in DOMAIN or any(type(case[key]) != type(value) for key, value in DOMAIN[0].items()):
            raise ValueError(f'Invalid proposal: {case}')
    if len({tuple(c[k] for k in DOMAIN[0]) for c in cases}) != len(cases):
        raise ValueError('Duplicate proposals')
    return cases


def measure(folder, program, project, *, paired=False):
    """Compile a post-session measurement with fixture locks and return its executable path."""
    audit = folder / project
    audit.mkdir()
    shutil.copyfile(folder / 'Suite/Suite.csproj', audit / 'Suite.csproj')
    shutil.copyfile(folder / 'Suite/packages.lock.json', audit / 'packages.lock.json')
    shutil.copyfile(program, audit / 'Program.cs')
    subprocess.run(['dotnet', 'restore', f'{project}/Suite.csproj', '--locked-mode'], cwd=folder, check=True)
    args = ['dotnet', 'build', f'{project}/Suite.csproj', '--no-restore']
    if paired:
        args.append('-p:DefineConstants=DECISION_PAIRS')
    subprocess.run(args, cwd=folder, check=True)
    return audit / 'bin/Debug/net10.0/Suite.dll'


def measure_json(folder, dll):
    """Run the clean measurement once and decode its observations, propagating any execution failure."""
    return json.loads(subprocess.check_output(['dotnet', str(dll)], cwd=folder, text=True, timeout=30))


def detections(folder, cases):
    """Run fixed cases twice and return reproducible independent contract mismatches."""
    found = replay(folder, cases)
    if found != replay(folder, cases):
        raise ValueError('Inconsistent suite replay')
    return found


def qualify(output, preflight=False, selection=False, paired=False):
    """Build and witness each mutation independently; only reproducible contract mismatches earn credit."""
    folders = output / 'fixtures'
    fixtures(folders, selection=selection, paired=paired)
    controls = json.loads((ROOT / 'controls.json').read_text())
    signatures = {}
    report = {}
    selected_report = {}
    for condition in CONDITIONS:
        folder = folders / condition
        cases = []
        if not preflight:
            receipts = json.loads((ROOT / 'sessions.json').read_text())
            install_source(ROOT / 'submissions' / f'{condition}.cs', folder / 'Suite/Cases.cs', receipts[condition])
            compile_suite(folder)
            cases = proposals(folder)
        selected_cases = None
        if selection and condition == 'cohesive':
            dll = measure(folder, ROOT / 'selection/Program.cs', 'Selection', paired=paired)
            generated = measure_json(folder, dll)
            if generated != measure_json(folder, dll):
                raise ValueError('SDK selection or its explanations changed on repeat')
            selected_cases = validate_cases([c['Input'] for c in generated['Cases']])
            if len(selected_cases) != BUDGET:
                raise ValueError(f'The post-session replay requires {BUDGET} distinct cases')
            stage = ROOT / ('decision-pairs' if paired else 'selection')
            manifest = json.loads((stage / 'sdk/dependency-manifest.json').read_text())
            selected_report = dict(sdkVersion=manifest['packageVersion'], sdkRevision=manifest['sourceRevision'],
                                   selectorSha256=hashlib.sha256((ROOT / 'selection/Program.cs').read_bytes()).hexdigest(),
                                   selection=generated, controls={})
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
                found = detections(folder, cases) if cases else []
                if selected_cases is not None:
                    selected_report['controls'][name] = dict(witness=witness, detections=detections(folder, selected_cases))
                record['controls'][name] = dict(witness=witness, mismatchingInputs=len(wrong), detections=found)
            finally:
                source.write_text(original)
    folder = folders / 'cohesive'
    budget = measure_json(folder, measure(folder, ROOT / 'audit/Program.cs', 'Audit'))
    (output / 'budget.json').write_text(json.dumps(budget, indent=2) + '\n')
    if selection:
        (output / 'selection.json').write_text(json.dumps(selected_report, indent=2) + '\n')
    (output / 'results.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--preflight', action='store_true', help='Validate clean and paired mutated behavior before authoring')
    parser.add_argument('--select', action='store_true', help='Replay the published post-session selector as well')
    parser.add_argument('--paired', action='store_true', help='Replay the decision-isolating SDK selector')
    args = parser.parse_args()
    qualify(args.output.resolve(), args.preflight, args.select or args.paired, args.paired)
