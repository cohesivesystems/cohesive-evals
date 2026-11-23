"""Build each fixture's offline probe and grade its complete state/command relation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import CONDITIONS
from packing_checks import TABLE, decision


def verify(fixtures, output):
    """Compare actual domain decisions to the independent contract, rejecting duplicate or extra cells."""
    expected = {}
    for state, commands in TABLE.items():
        for command in commands:
            reply, destination = decision('probe', state, command)
            expected[state, command] = destination if reply[0] == 200 else None
    results = {}
    for condition in CONDITIONS:
        project = fixtures / condition / 'tests/LifecycleProbe/LifecycleProbe.csproj'
        subprocess.run(['dotnet', 'build', str(project), '-p:RestoreLockedMode=true', '-v:q'], check=True, cwd=project.parent)
        raw = subprocess.check_output(['dotnet', 'run', '--no-build', '--project', str(project)], cwd=project.parent)
        rows = json.loads(raw)
        actual = {(r['state'], r['command']): r['destination'] for r in rows}
        if len(rows) != len(actual) or actual != expected:
            raise AssertionError((condition, 'offline lifecycle relation', rows))
        results[condition] = rows
        if condition == 'cohesive':
            raw = subprocess.check_output(['dotnet', 'run', '--no-build', '--project', str(project),
                                           '--', '--coverage-control'], cwd=project.parent)
            observed = json.loads(raw)
            if observed['accepted'] or 'transitions.compilation.machine.coverage' not in observed['diagnostics']:
                raise AssertionError(('machine coverage diagnostic', observed))
            results['cohesiveCoverageControl'] = observed
    output.write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    verify(args.fixtures.resolve(), args.output)
