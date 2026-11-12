#!/usr/bin/env python3
"""Replay the original five acceptance cases without invoking a model."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from run import digest, manifest, write_json

ROOT = Path(__file__).resolve().parent


def normalize(record):
    return {**{key: record[key] for key in ('validity', 'outcome')},
            **{key: record['gates'][key] for key in ('contractBuild', 'visibleTests', 'hiddenChecks', 'treatmentIntegrity')},
            'failedObligations': [o['id'] for o in record['obligations'] if o['status'] == 'failed'],
            'notEvaluatedObligations': [o['id'] for o in record['obligations'] if o['status'] == 'notEvaluated']}


def check_evidence(folder, record):
    for relative in list(record['evidence'].values()) + [record['submission']['finalPatch'],
            record['workspace']['preManifest'], record['workspace']['postManifest'], 'agent/stdout.log', 'agent/stderr.log']:
        if relative:
            assert (folder/relative).is_file(), relative
    assert digest(folder/'inputs/config.json') == record['configuration']['configSha256']
    for patch in record['submission']['appliedInputs']:
        assert digest(folder/patch['path']) == patch['sha256']
    assert json.loads((folder/record['workspace']['postManifest']).read_text()) == manifest(folder/'workspace')
    assert not (folder/'scoring/submission/.git').exists()
    assert subprocess.check_output(['git', '-C', str(folder/'workspace'), 'rev-list', '--count', 'HEAD'], text=True).strip() == '1'
    assert record['agent']['invoked'] is False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_root', nargs='?', type=Path)
    args = parser.parse_args()
    output = args.output_root or Path(tempfile.mkdtemp(prefix='cohesive-runner-validation-'))
    output = output.resolve()
    cases = json.loads((ROOT/'validation-cases.json').read_text())['cases']
    results = []
    for case in cases:
        command = [sys.executable, '-B', str(ROOT/'run.py'), '--condition', case['condition'], '--run-id', case['id'], '--output-root', str(output)]
        for patch in case['patches']:
            command += ['--patch', patch]
        subprocess.run(command, check=True)
        folder = output/case['id']
        record = json.loads((folder/'run.json').read_text())
        actual = normalize(record)
        assert actual == case['expected'], (case['id'], case['expected'], actual)
        check_evidence(folder, record)
        results.append({'id': case['id'], 'passed': True, 'recordSha256': digest(folder/'run.json')})
    write_json(output/'validation-report.json', {'passed': True, 'cases': results})
    print(f'Validated {len(results)} runner cases.\nEvidence: {output}')


if __name__ == '__main__':
    main()
