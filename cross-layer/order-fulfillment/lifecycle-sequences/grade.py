"""Rebuild pinned fixtures and compare frozen sequences on matched, witnessed domain defects."""
import argparse
from collections import deque
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'partial-shipping'))
from fixture import APP, CONDITIONS, call, compile_suite, fixtures, install_source

COMMANDS = ['Pack', 'Unpack', 'Hold', 'Release', *(f'Ship:{q}' for q in range(-1, 5))]
REQUIRED = ['Pack', 'Ship:1', 'Hold', 'Ship:2', 'Release', 'Ship:2']
START = ('Submitted', False, 3)


def step(state, command):
    """Predict acceptance and the next public state from the pinned contract alone."""
    status, held, remaining = state
    if command in ('Pack', 'Unpack') and status in ('Submitted', 'Packed'):
        return True, ('Packed' if command == 'Pack' else 'Submitted', held, remaining)
    if status == 'Packed':
        if command in ('Hold', 'Release'):
            return True, (status, command == 'Hold', remaining)
        if command.startswith('Ship:') and not held:
            quantity = int(command.split(':')[1])
            if 1 <= quantity <= remaining:
                left = remaining - quantity
                return True, ('Packed' if left else 'Shipped', held, left)
    return False, state


def coverage():
    """Exercise every next command after a shortest clean prefix to every reachable state."""
    queue = deque([(START, [])])
    seen = {START}
    sequences = []
    while queue:
        state, prefix = queue.popleft()
        for command in COMMANDS:
            path = [*prefix, command]
            sequences.append(path)
            _, after = step(state, command)
            if after not in seen:
                seen.add(after)
                queue.append((after, path))
    return sequences


def check_budget(sequences):
    """Reject duplicate, invalid or oversized proposals and enforce the common scenario."""
    if not 1 <= len(sequences) <= 4 or len(set(map(tuple, sequences))) != len(sequences):
        raise ValueError('Invalid sequence count or duplicate sequences')
    for commands in sequences:
        if not 1 <= len(commands) <= 8 or any(c not in COMMANDS for c in commands):
            raise ValueError(f'Invalid sequence: {commands}')
    if not any(s[i:i + len(REQUIRED)] == REQUIRED for s in sequences for i in range(len(s))):
        raise ValueError('Missing required scenario')


def differences(folder, sequences, *, first_only=False):
    """Return observed step mismatches, optionally only the first in each sequence. Execution or protocol failures abort the run."""
    result = call(folder, 'execute', sequences)
    if result['sequences'] != sequences:
        raise ValueError('Sequence echo mismatch')
    failures = []
    for index, (commands, trace) in enumerate(zip(sequences, result['traces'], strict=True)):
        state = START
        for number, (command, actual) in enumerate(zip(commands, trace, strict=True), 1):
            accepted, state = step(state, command)
            status, held, remaining = state
            expected = dict(Accepted=accepted, Status=status, Id='order-A', Hold=held, Remaining=remaining)
            already_failed = failures and failures[-1]['sequence'] == index
            if actual != expected and not (first_only and already_failed):
                failures.append(dict(sequence=index, step=number, expected=expected, actual=actual))
    return failures


def generate(output, *, relock=False):
    """Run the published selector twice on an isolated clean model before loading any controls."""
    stage = ROOT / 'replay'
    generated = output / 'generator'
    fixtures(generated, stage=stage, relock=relock)
    folder = generated / 'cohesive'
    subprocess.run(['git', 'apply', str(ROOT / 'reference/cohesive.patch')], cwd=folder, check=True)
    suite = folder / 'Suite'
    for name in ['Adapter.cs', 'Cases.cs']:
        (suite / name).unlink()
    shutil.copyfile(stage / 'Program.cs', suite / 'Program.cs')
    compile_suite(folder)
    command = ['dotnet', 'Suite/bin/Debug/net10.0/Suite.dll']
    runs = [subprocess.check_output(command, cwd=folder, input=json.dumps(REQUIRED),
                                    text=True, timeout=60) for _ in range(2)]
    if runs[0] != runs[1]:
        raise ValueError('Unstable SDK selection')
    selection = json.loads(runs[0])
    check_budget(selection['sequences'])
    if len(selection['sequences']) != 4:
        raise ValueError('Expected four SDK-selected sequences')
    return selection


def grade(output, *, replay=False, relock=False):
    """Require clean equivalence and matched control signatures before reporting any scores."""
    selection = generate(output, relock=relock) if replay else None
    selected = selection['sequences'] if selection else []
    replay_controls = {}
    folder_root = output / 'fixtures'
    fixtures(folder_root, selection=True, paired=True)
    sessions = json.loads((ROOT / 'sessions.json').read_text())
    panel = json.loads((ROOT / 'panel.json').read_text())
    qualification = coverage() + [c['witness'] for c in panel]
    signatures = {}
    report = {}
    for condition in CONDITIONS:
        folder = folder_root / condition
        suite = folder / 'Suite'
        subprocess.run(['git', 'apply', str(ROOT / 'reference' / f'{condition}.patch')], cwd=folder, check=True)
        for name in ['Cases.cs', 'Adapter.cs']:
            (suite / name).unlink()
        shutil.copyfile(ROOT / 'Program.cs', suite / 'Program.cs')
        install_source(ROOT / 'submissions' / f'{condition}.cs', suite / 'Submission.cs', sessions[condition])
        compile_suite(folder)
        propose = ['dotnet', 'Suite/bin/Debug/net10.0/Suite.dll']
        runs = [subprocess.check_output(propose, cwd=folder, timeout=30) for _ in range(2)]
        if runs[0] != runs[1]:
            raise ValueError('Unstable clean suite')
        sequences = json.loads(runs[0])['sequences']
        check_budget(sequences)
        if differences(folder, qualification + sequences + selected):
            raise ValueError(f'{condition}: clean contract mismatch')
        record = report[condition] = dict(sequences=sequences, controls={})
        candidate = folder / APP / ('Domain.cs' if condition == 'conventional' else 'FulfillmentDomain.cs')
        original = candidate.read_text()
        for index, control in enumerate(panel):
            name = control['name']
            before, after = control[condition]
            if original.count(before) != 1:
                raise ValueError(f'{name}: source anchor drift')
            try:
                candidate.write_text(original.replace(before, after))
                compile_suite(folder)
                signature = differences(folder, qualification)
                witness = len(qualification) - len(panel) + index
                if not any(f['sequence'] == witness for f in signature):
                    raise ValueError(f'{name}: missing witness')
                if signature != signatures.setdefault(name, signature):
                    raise ValueError(f'{name}: asymmetric traces on qualification paths')
                detected = differences(folder, sequences, first_only=True)
                if detected != differences(folder, sequences, first_only=True):
                    raise ValueError(f'{name}: unstable replay')
                record['controls'][name] = detected
                if selection:
                    sdk_hits = differences(folder, selected, first_only=True)
                    if sdk_hits != differences(folder, selected, first_only=True):
                        raise ValueError(f'{name}: unstable SDK replay')
                    if sdk_hits != replay_controls.setdefault(name, sdk_hits):
                        raise ValueError(f'{name}: different SDK replay across frozen executors')
            finally:
                candidate.write_text(original)
    if selection:
        selection['controls'] = replay_controls
        (output / 'replay.json').write_text(json.dumps(selection, indent=2) + '\n')
    result = dict(qualificationPaths=len(qualification), conditions=report)
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='Fresh directory for disposable builds and evidence')
    parser.add_argument('--replay', action='store_true', help='Grade sequences selected on the clean SDK model')
    parser.add_argument('--relock', action='store_true', help='Regenerate the selector project locks')
    args = parser.parse_args()
    grade(args.output.resolve(), replay=args.replay or args.relock, relock=args.relock)
