"""Freeze two clean selector suites, then reveal and grade a preregistered random defect panel."""
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from fixture import fixtures

PROTOCOL = json.loads((HERE / 'protocol.json').read_text())
DOMAIN = [dict(Phase=p, Embargo=e, Limit=l, Risk=r)
          for p, e, l, r in product(range(4), (False, True), range(1, 5), range(-1, 7))]


def expected(x):
    """Public contract: queued, clear articles accept nonnegative scores and store the actual score."""
    allowed = x['Phase'] == 0 and not x['Embargo'] and x['Risk'] >= 0
    phase = (1 if x['Risk'] <= x['Limit'] else 2) if allowed else x['Phase']
    return dict(Accepted=allowed, Outcome=allowed,
                State=dict(Id='fixture', Phase=phase, Embargo=x['Embargo'], Limit=x['Limit'],
                           LastScore=x['Risk'] if allowed else -9))


def write(path, data):
    """Write reproducible evidence with stable field and list order."""
    path.write_text(json.dumps(data, indent=2) + '\n')


def sha(value):
    """Hash UTF-8 protocol strings or raw artifact bytes."""
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def compile_model(folder, fault=None):
    """Build the clean model or a single catalog variant; errors abort without detection credit."""
    project = folder / 'Panel'
    args = ['dotnet', 'build', 'Panel.csproj', '--no-restore', '--no-incremental']
    if fault:
        args.append('-p:DefineConstants=' + fault)
    subprocess.run(args, cwd=project, check=True, timeout=120)


def run(folder, mode, inputs=None):
    """Execute the locked panel assembly and require valid JSON output."""
    dll = folder / 'Panel/bin/Debug/net10.0/Panel.dll'
    return json.loads(subprocess.check_output(['dotnet', str(dll), mode], cwd=folder,
                     input=json.dumps(inputs), text=True, timeout=60))


def freeze(output):
    """Generate each suite twice on clean code with no access to the draw seed."""
    suites = {}
    for version in ['reference', 'paired']:
        base = output / version
        fixtures(base, selection=True, paired=version == 'paired')
        folder = base / 'cohesive'
        panel = folder / 'Panel'
        panel.mkdir()
        shutil.copyfile(folder / 'Suite/Suite.csproj', panel / 'Panel.csproj')
        shutil.copyfile(folder / 'Suite/packages.lock.json', panel / 'packages.lock.json')
        shutil.copyfile(HERE / 'Program.cs', panel / 'Program.cs')
        subprocess.run(['dotnet', 'restore', 'Panel.csproj', '--locked-mode'], cwd=panel, check=True)
        compile_model(folder)
        cases = run(folder, 'select')
        if (cases != run(folder, 'select') or len(cases) != PROTOCOL['caseBudget']
                or len({json.dumps(c, sort_keys=True) for c in cases}) != len(cases)
                or any(c not in DOMAIN for c in cases)):
            raise ValueError(f'Invalid or unstable {version} suite')
        if run(folder, 'execute', DOMAIN) != [expected(x) for x in DOMAIN]:
            raise ValueError(f'{version} clean reference disagrees with the oracle')
        suites[version] = cases
    write(output / 'suites.json', suites)


def score(output, seed_path):
    """Verify the committed draw and fixed suites, confirm each fault over the entire domain and replay twice."""
    seed = seed_path.read_text().strip()
    if sha(seed) != PROTOCOL['seedCommitment']:
        raise ValueError('Draw commitment mismatch')
    pinned = HERE / 'suites.json'
    if pinned.read_bytes() != (output / 'suites.json').read_bytes():
        raise ValueError('The suites differ from the pre-reveal freeze')
    suites = json.loads(pinned.read_text())
    draw = sorted(PROTOCOL['catalog'], key=lambda name: sha(seed + '/' + name))[:PROTOCOL['drawSize']]
    report = dict(seed=seed, suitesSha256=sha(pinned.read_bytes()), domainSize=len(DOMAIN), controls={})
    for name in draw:
        control = {}
        full = None
        for version, cases in suites.items():
            folder = output / version / 'cohesive'
            compile_model(folder, name)
            rows = run(folder, 'execute', DOMAIN)
            if full is not None and full != rows:
                raise ValueError(f'Unmatched mutant: {name}')
            full = rows
            wrong = [dict(input=c, expected=expected(c), actual=a) for c, a in zip(DOMAIN, rows, strict=True) if a != expected(c)]
            if not wrong:
                raise ValueError(f'Unconfirmed mutant: {name}')
            actual = run(folder, 'execute', cases)
            if actual != run(folder, 'execute', cases):
                raise ValueError(f'Unstable {version}/{name} replay')
            control[version] = [c for c, a in zip(cases, actual, strict=True) if a != expected(c)]
        report['controls'][name] = dict(witness=wrong[0], mismatchingInputs=len(wrong), detections=control)
    write(output / 'comparison.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--seed', type=Path, help='Score the frozen suites using the revealed seed')
    args = parser.parse_args()
    if args.seed:
        score(args.output.resolve(), args.seed)
    else:
        freeze(args.output.resolve())
