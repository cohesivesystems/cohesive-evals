"""Replay frozen proposals against independently witnessed single-source Ship defects."""
import argparse
import itertools
import json
from pathlib import Path
import shutil
import subprocess

from prepare import APP, CONDITIONS, ROOT, build


def call(folder, command, cases=None):
    """Execute a built offline adapter; malformed output or an execution error earns no credit."""
    dll = folder / 'Suite/bin/Debug/net10.0/Suite.dll'
    result = subprocess.run(['dotnet', str(dll), command], cwd=folder, check=True,
                            input=json.dumps(cases), capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)


def observation(case):
    """Independent shipping contract: preserve identity and hold, advance only a clear Packed order."""
    accepted = case['Status'] == 'Packed' and not case['Hold']
    return dict(Accepted=accepted, Status='Shipped' if accepted else case['Status'], Id='order-A', Hold=case['Hold'])


def mismatches(cases, actual):
    """Name the observable input and both outcomes for each contract violation."""
    return [dict(input=c, expected=observation(c), actual=a) for c, a in zip(cases, actual, strict=True)
            if observation(c) != a]


def run(output):
    """Build clean fixtures, freeze deterministic proposals, and replay them on each confirmed defect."""
    fixtures = output / 'fixtures'
    build(fixtures)
    panel = json.loads((ROOT / 'controls.json').read_text())
    domain = [dict(Status=s, Hold=h) for s, h in itertools.product(
        ['Draft', 'Submitted', 'Packed', 'Cancelled', 'Shipped'], [False, True])]
    report = {}
    for condition in CONDITIONS:
        folder = fixtures / condition
        shutil.copyfile(ROOT / 'submissions' / f'{condition}.cs', folder / 'Suite/Cases.cs')
        source = folder / APP / ('Domain.cs' if condition == 'conventional' else 'FulfillmentDomain.cs')
        original = source.read_text()
        def compile_suite():
            """Compile the candidate and suite; a build error aborts grading."""
            subprocess.run(['dotnet', 'build', 'Suite/Suite.csproj', '--no-restore', '--no-incremental'],
                           cwd=folder, check=True, stdout=subprocess.DEVNULL, timeout=90)
        compile_suite()
        cases = call(folder, 'propose')
        if (cases != call(folder, 'propose') or not 0 < len(cases) <= 10
                or any(type(c.get('Hold')) is not bool or c not in domain for c in cases)
                or len({(c['Status'], c['Hold']) for c in cases}) != len(cases)):
            raise ValueError(f'{condition}: invalid or unstable proposals')
        if mismatches(domain, call(folder, 'execute', domain)):
            raise ValueError(f'{condition}: reference fails independent contract')
        record = report[condition] = dict(cases=cases, controls={})
        for control in panel:
            before, after = control[condition]
            if original.count(before) != 1:
                raise ValueError(f"Mutation anchor drift: {condition}/{control['id']}")
            try:
                source.write_text(original.replace(before, after))
                compile_suite()
                witness = mismatches(domain, call(folder, 'execute', domain))
                found = mismatches(cases, call(folder, 'execute', cases))
                if found != mismatches(cases, call(folder, 'execute', cases)):
                    raise ValueError('Inconsistent replay')
                if [row['input'] for row in witness] != [dict(zip(('Status','Hold'),control['witness']))]:
                    raise ValueError(f"Unconfirmed or nonisolated defect {control['id']}: {witness}")
                record['controls'][control['id']] = dict(witness=witness[0], detections=found)
            finally:
                source.write_text(original)
    for control in panel:
        outcomes = [r['controls'][control['id']]['witness'] for r in report.values()]
        if outcomes[0] != outcomes[1]:
            raise ValueError(f"Unmatched public behavior: {control['id']}")
    (output / 'results.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    run(parser.parse_args().output.resolve())
