#!/usr/bin/env python3
"""Independent, versioned HTTP/physical-state witnesses for the precedence revision."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'suites'))
import fixture
# Reuse the existing lifecycle, HTTP client and read-only SQL observer.
ao1 = fixture.ao1
sys.path.insert(0, str(ao1.ROOT.parent / 'portable-validation/pv1'))
pv1 = ao1.load('mv1_http_world', ao1.ROOT.parent / 'portable-validation/pv1/verify.py')
from runtime import verification_run
checks = ao1.load('mv1_http_assertions', ao1.ROOT / 'checks.py')

# Explicit expected observations, independent of the offline generator and oracle.
# name, stock, limit, quarantine, quantity, original outcome, revised outcome
ROWS = [
    ('negative', 0, 1, True, -1, 'InvalidQuantity', 'InvalidQuantity'),
    ('zero', 0, 1, True, 0, 'InvalidQuantity', 'InvalidQuantity'),
    ('overlap', 0, 1, True, 2, 'InventoryQuarantined', 'QuantityLimitExceeded'),
    ('quarantine', 7, 4, True, 3, 'InventoryQuarantined', 'InventoryQuarantined'),
    ('limit', 0, 1, False, 2, 'QuantityLimitExceeded', 'QuantityLimitExceeded'),
    ('short', 0, 4, False, 1, 'InsufficientStock', 'InsufficientStock'),
    ('exact', 4, 4, False, 4, 'ReservedAndSubmitted', 'ReservedAndSubmitted'),
    ('below', 7, 4, False, 3, 'ReservedAndSubmitted', 'ReservedAndSubmitted'),
]


def seed():
    return {'orders': [dict(id=n, status='Draft') for n, *_ in ROWS],
            'inventory': [dict(sku=n, available=s, maxPerOrder=m, quarantined=q) for n,s,m,q,*_ in ROWS],
            'reservations': []}


def run(fixtures, output):
    records = {}
    with verification_run(output, 'mv1', checks.BehavioralFailure) as session:
        for version in fixture.VERSIONS:
            records[version] = {}
            for condition in fixture.CONDITIONS:
                session.condition = version + '/' + condition
                folder = fixtures / version / 'references' / condition
                digest = ao1.build_tools.verify_build(folder)
                observations = []
                for mode in ('http', 'batch'):
                    world = pv1.World(folder, output / version / condition / mode, session.container,
                                      session.port, condition, seed())
                    try:
                        test = checks.Checks(world)
                        test.expected = seed()
                        requests = [dict(requestId='mv1-' + n, orderId=n, sku=n, quantity=q)
                                    for n,_,_,_,q,*_ in ROWS]
                        expected = [row[5 if version == 'original' else 6] for row in ROWS]
                        items = test.items(mode, requests, expected, '03', 'versioned precedence')
                        for row in ROWS:
                            if row[5] != 'ReservedAndSubmitted':
                                continue
                            name, stock, _, _, quantity, *_ = row
                            next(x for x in test.expected['orders'] if x['id'] == name)['status'] = 'Submitted'
                            next(x for x in test.expected['inventory'] if x['sku'] == name)['available'] = stock - quantity
                            test.expected['reservations'].append(dict(id=name, orderId=name, sku=name, quantity=quantity))
                        test.unchanged('10', 'versioned physical state')
                        # Replay across the other API surface preserves identity, result and all facts.
                        other = 'batch' if mode == 'http' else 'http'
                        replay = test.items(other, requests, expected, '10', 'versioned replay')
                        test.check(replay == items, '10', 'versioned replay', (items, replay))
                        test.unchanged('10', 'versioned replay preservation')
                        observations.append({'mode': mode, 'assertions': test.counts, 'facts': world.facts()})
                        (world.output / 'trace.json').write_text(json.dumps(test.trace, indent=2) + '\n')
                    finally:
                        world.close()
                if ao1.build_tools.verify_build(folder) != digest:
                    raise ValueError('Production inputs changed during HTTP verification')
                records[version][condition] = {'buildManifestSha256': digest, 'observations': observations}
            left = records[version]['conventional']['observations']
            right = records[version]['cohesive']['observations']
            for a, b in zip(left, right):
                checks.require(checks.canonical(a['facts']) == checks.canonical(b['facts']),
                               'MV1-10', 'condition equivalence', (a, b))
        session.report(records)
    print('MV1 versioned HTTP checks passed', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run(args.fixtures.resolve(), args.output.resolve())
