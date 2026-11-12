#!/usr/bin/env python3
"""Inject infrastructure faults around a real known-correct build; retain evidence."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from run import ROOT, digest, write_json
from validate import check_evidence

# This wrapper delegates to the real SDK. It only modifies the selected failure
# boundary, so all earlier stages must pass for a case to qualify.
WRAPPER = '''#!{python}
import json, os, subprocess, sys
args = sys.argv[1:]
mode = os.environ['RUNNER_TEST_FAULT']
real = os.environ['RUNNER_REAL_DOTNET']
if mode == 'restore-outage' and args[0] == 'restore':
    sys.exit(70)
if mode == 'build-outage' and args[0] == 'build':
    sys.exit(70)
if mode == 'visible-outage' and args[0] == 'test':
    sys.exit(70)
if args[0].endswith('LoadSearch.Oracle.dll'):
    if mode == 'oracle-outage': sys.exit(70)
    if mode == 'missing-report': sys.exit(0)
    path = args[args.index('--output')+1]
    if mode == 'malformed-report':
        open(path, 'w').write('{{bad json')
        sys.exit(0)
    code = subprocess.call([real, *args])
    if code: sys.exit(code)
    report = json.load(open(path))
    if mode == 'empty-obligations': report['obligations'] = []
    if mode == 'duplicate-obligation': report['obligations'][1] = report['obligations'][0]
    if mode == 'wrong-condition': report['condition'] = 'cohesive'
    json.dump(report, open(path, 'w'))
    sys.exit(70 if mode == 'exit-mismatch' else 0)
os.execv(real, [real, *args])
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_root', nargs='?', type=Path)
    args = parser.parse_args()
    output = (args.output_root or Path(tempfile.mkdtemp(prefix='runner-failure-validation-'))).resolve()
    real = shutil.which(os.environ.get('DOTNET_CLI', 'dotnet'))
    assert real, 'SDK required'
    cases = {
        'restore-outage': 'dependency restore failed', 'build-outage': 'without submission compiler diagnostics',
        'visible-outage': 'no TRX report', 'oracle-outage': 'Missing or malformed oracle report',
        'missing-report': 'Missing or malformed oracle report', 'malformed-report': 'Missing or malformed oracle report',
        'empty-obligations': 'missing/duplicate/unexpected IDs', 'duplicate-obligation': 'missing/duplicate/unexpected IDs',
        'wrong-condition': 'condition', 'exit-mismatch': 'unexpected process exit 70'}
    records = []
    with tempfile.TemporaryDirectory(prefix='runner-fault-driver-') as temp:
        wrapper = Path(temp)/'dotnet-fault'
        wrapper.write_text(WRAPPER.format(python=sys.executable)); wrapper.chmod(0o755)
        for name, reason in cases.items():
            command = [sys.executable, '-B', str(ROOT/'run.py'), '--condition', 'conventional', '--run-id', name,
                       '--output-root', str(output), '--patch', 'relations/oracle/load-search-mapping/qualification/patches/conventional/LSM-QUAL-GOOD-CONV.patch']
            result = subprocess.run(command, env=dict(os.environ, DOTNET_CLI=str(wrapper), RUNNER_REAL_DOTNET=real, RUNNER_TEST_FAULT=name))
            folder = output/name; record = json.loads((folder/'run.json').read_text())
            assert result.returncode == 2 and record['validity'] == 'invalid' and record['outcome'] == 'notScored', (name, record)
            assert reason in record['invalidReason'], (name, record['invalidReason'])
            assert all(o['status'] == 'notEvaluated' for o in record['obligations']), name
            check_evidence(folder, record)
            before = digest(folder/'run.json')
            duplicate = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            assert duplicate.returncode == 73 and digest(folder/'run.json') == before
            records.append({'id': name, 'passed': True, 'recordSha256': before})
    write_json(output/'validation-report.json', {'passed': True, 'cases': records})
    print(f'Validated {len(records)} infrastructure failure cases. Evidence: {output}')


if __name__ == '__main__':
    main()
