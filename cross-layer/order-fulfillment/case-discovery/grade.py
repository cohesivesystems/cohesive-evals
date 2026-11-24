"""Replay frozen proposals against independently witnessed single-source Ship defects."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

from prepare import APP, CONDITIONS, ROOT, build


def call(folder, command, cases=None):
    """Execute a built offline adapter; malformed output or an execution error earns no credit."""
    dll = folder / 'Suite/bin/Debug/net10.0/Suite.dll'
    result = subprocess.run(['dotnet', str(dll), command], cwd=folder, check=True,
                            input=json.dumps(cases), capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)


def stable_propose(folder, domain, maximum):
    """Return the ordered clean proposals if two runs agree and satisfy the session budget."""
    cases = call(folder, 'propose')
    if cases != call(folder, 'propose'):
        raise ValueError(f'{folder.name}: unstable proposal order or contents')
    if not isinstance(cases, list) or not 0 < len(cases) <= maximum:
        raise ValueError(f'{folder.name}: invalid proposal count')
    if any(not isinstance(c, dict) or type(c.get('Hold')) is not bool or c not in domain for c in cases):
        raise ValueError(f'{folder.name}: invalid proposal')
    if len({(c['Status'], c['Hold']) for c in cases}) != len(cases):
        raise ValueError(f'{folder.name}: duplicate proposal')
    return cases


def install_source(source, target, pin):
    """Install exactly the source bytes identified by the submission or post-session receipt."""
    contents = source.read_bytes()
    if hashlib.sha256(contents).hexdigest() != pin['sha256']:
        raise ValueError(f'Case source changed: {source}')
    target.write_bytes(contents)


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
    sessions = json.loads((ROOT / "sessions.json").read_text())
    report = {}
    for condition in CONDITIONS:
        folder = fixtures / condition
        submitted = ROOT / 'submissions' / f'{condition}.cs'
        suite = folder / 'Suite/Cases.cs'
        author = sessions['authors'][condition]
        install_source(submitted, suite, author)
        source = folder / APP / ('Domain.cs' if condition == 'conventional' else 'FulfillmentDomain.cs')
        original = source.read_text()
        def compile_suite():
            """Compile the candidate and suite; a build error aborts grading."""
            subprocess.run(['dotnet', 'build', 'Suite/Suite.csproj', '--no-restore', '--no-incremental'],
                           cwd=folder, check=True, stdout=subprocess.DEVNULL, timeout=90)
        compile_suite()
        maximum = sessions['maximumCases']
        cases = stable_propose(folder, domain, maximum)
        if replay := sessions['postSessionReplays'].get(condition):
            try:
                install_source(ROOT / 'replay' / f'{condition}.cs', suite, replay)
                compile_suite()
                if stable_propose(folder, domain, maximum) != cases:
                    raise ValueError(f'{condition}: replay differs from the frozen proposal')
            finally:
                install_source(submitted, suite, author)
            compile_suite()  # The clean reference and every mutant execute the frozen suite.
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
                try:
                    witness = mismatches(domain, call(folder, 'execute', domain))
                except subprocess.CalledProcessError as error:
                    code = control.get('expectedModelRejection', {}).get(condition)
                    if not code or f'Code = {code}, Severity = Error' not in (error.stderr or ''):
                        raise RuntimeError(f"{condition}/{control['id']} adapter failed: {error.stderr}") from error
                    record['controls'][control['id']] = dict(classification='model-compilation-rejection', diagnostic=code)
                    (output / f"{condition}-{control['id']}-diagnostic.txt").write_text(error.stderr)
                    continue
                if condition in control.get('expectedModelRejection', {}):
                    raise ValueError(f"{condition}/{control['id']}: expected model rejection was absent")
                found = mismatches(cases, call(folder, 'execute', cases))
                if found != mismatches(cases, call(folder, 'execute', cases)):
                    raise ValueError('Inconsistent replay')
                if [row['input'] for row in witness] != [dict(zip(('Status','Hold'),control['witness']))]:
                    raise ValueError(f"Unconfirmed or nonisolated defect {control['id']}: {witness}")
                record['controls'][control['id']] = dict(witness=witness[0], detections=found)
            finally:
                source.write_text(original)
    for control in panel:
        observations = [r['controls'][control['id']] for r in report.values()]
        if any('witness' not in row for row in observations):
            continue
        outcomes = [row['witness'] for row in observations]
        if outcomes[0] != outcomes[1]:
            raise ValueError(f"Unmatched public behavior: {control['id']}")
    sdk = json.loads((ROOT / 'sdk/dependency-manifest.json').read_text())
    results = output / 'results.json'
    results.write_text(json.dumps(report, indent=2) + '\n')
    provenance = {
        'authoringProtocolCommit': sessions['protocolCommit'],
        'gradingSdkVersion': sdk['packageVersion'],
        'gradingSdkRevision': sdk['sourceRevision'],
        'lockSha256': {name: hashlib.sha256((fixtures / 'cohesive' / path / 'packages.lock.json').read_bytes()).hexdigest()
                       for name, path in [('app', APP), ('suite', Path('Suite'))]},
        'resultsSha256': hashlib.sha256(results.read_bytes()).hexdigest(),
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    run(parser.parse_args().output.resolve())
