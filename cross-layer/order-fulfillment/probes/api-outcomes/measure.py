#!/usr/bin/env python3
"""Summarize pinned AO1 evidence; never infer effort or comparative rates from counts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONDITIONS = ('conventional', 'cohesive')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def patch_counts(text):
    files = {}
    current = None
    for line in text.splitlines():
        if line.startswith('+++ b/'):
            current = line[6:]
            if current in files: raise ValueError('Duplicate patch file')
            files[current] = {'added': 0, 'removed': 0}
        elif current and line.startswith('+'):
            files[current]['added'] += 1
        elif current and line.startswith('-') and not line.startswith('--- '):
            files[current]['removed'] += 1
    return files

def behavioral_pairs(report):
    if report.get('passed') is not True or report.get('complete') is not True:
        raise ValueError('Qualification is incomplete')
    groups = {c: {} for c in CONDITIONS}
    controls = set()
    for row in report['cases']:
        condition, name = row['condition'], row['case']
        if condition not in groups or row.get('passed') is not True:
            raise ValueError('Unqualified condition/case')
        if not row.get('buildManifestSha256'): raise ValueError('Missing build provenance')
        if name == 'known-good':
            if row['failure'] is not None or condition in controls: raise ValueError('Invalid control')
            controls.add(condition)
            continue
        failure = row['failure']
        if not failure or failure.get('kind') != 'behavioral' or not failure.get('assertion') or not failure.get('obligation'):
            raise ValueError('Not a named behavioral detection')
        if name in groups[condition]: raise ValueError('Duplicate case')
        groups[condition][name] = failure
    if controls != set(CONDITIONS): raise ValueError('Missing known-good control')
    common = sorted(set.intersection(*(set(g) for g in groups.values())))
    paired = []
    for name in common:
        identities = {(g[name]['obligation'], g[name]['assertion']) for g in groups.values()}
        if len(identities) != 1: raise ValueError('Shared case name has different target assertions')
        obligation, assertion = identities.pop()
        paired.append({'fault': name, 'obligation': obligation, 'assertion': assertion,
                       'observedEnforcedDetection': {c: 'independent verifier' for c in CONDITIONS}})
    return paired, {c: sorted(set(g) - set(common)) for c, g in groups.items()}

def measure(root=ROOT):
    index = json.loads((root/'evidence.json').read_text())
    consumed = {'evidence.json': digest(root/'evidence.json')}
    def verified(relative, expected):
        path = root/relative
        actual = digest(path)
        if actual != expected: raise ValueError('Evidence drift: '+relative)
        consumed[relative] = actual
        return path
    reports = {}
    for name in ('qualification', 'diagnostics', 'ao1', 'alias', 'retained-typed', 'retained-pv1', 'retained-g0-g3'):
        relative = 'evidence/'+name+'.json'
        path = verified(relative, index['evidenceSha256'][name+'.json'])
        reports[name] = json.loads(path.read_text())
        if reports[name].get('passed') is not True or reports[name].get('complete', True) is not True:
            raise ValueError('Incomplete evidence: '+name)
    changes = {}
    for c in CONDITIONS:
        relative = 'reference/'+c+'.patch'
        path = verified(relative, index['sourceSha256']['probes/api-outcomes/'+relative])
        manifest = verified('reference/'+c+'.json', index['sourceSha256']['probes/api-outcomes/reference/'+c+'.json'])
        files = patch_counts(path.read_text())
        if set(files) != set(json.loads(manifest.read_text())): raise ValueError('Unmanifested patch paths')
        categories = {}
        for category, paths in [('application', [p for p in files if p.endswith('.cs')]),
                                ('schemas', [p for p in files if p.endswith('.json')]),
                                ('contractDocumentation', [p for p in files if p.endswith('.md')])]:
            categories[category] = {'files': len(paths), **{k: sum(files[p][k] for p in paths) for k in ('added','removed')}}
        changes[c] = {'categories': categories, 'perFile': files}
    paired, unpaired = behavioral_pairs(reports['qualification'])
    static = reports['diagnostics']['cases']
    if any(r.get('passed') is not True or not r.get('diagnosticLines') or not r.get('inputsSha256') for r in static):
        raise ValueError('Unqualified static evidence')
    # This is the only shared conceptual type-negative in the recorded fixtures.
    typed = [r for r in static if r['case'] == 'wrong-input-type']
    if len(typed) != 2 or {r['condition'] for r in typed} != set(CONDITIONS) or any(r['stage'] != 'compile' for r in typed):
        raise ValueError('Missing paired type controls')
    return {'applicationRevision': '7db195a2b0c6fbc1da1f0d284708f46c21922320',
            'inputsSha256': consumed, 'changes': changes,
            'pairedBehavioralFaults': paired, 'unpairedBehavioralFaults': unpaired,
            'pairedTypeFault': {r['condition']: {'case': r['case'], 'stage': r['stage'], 'diagnostic': r['diagnostic']} for r in typed},
            'unpairedStaticFixtures': [{k:r[k] for k in ('condition','case','stage','diagnostic')} for r in static if r['case'] != 'wrong-input-type'],
            'effort': {'developmentTime': None, 'repairTime': None, 'repairIterations': None, 'repairRegressions': None}}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify the committed summary without rewriting it')
    args = parser.parse_args()
    text = json.dumps(measure(), indent=2)+'\n'
    output = ROOT/'measurements.json'
    if args.check:
        if output.read_text() != text: raise SystemExit('Measurement summary drift')
        print('AO1 measurements match pinned evidence')
    else:
        output.write_text(text)
        print(output)
