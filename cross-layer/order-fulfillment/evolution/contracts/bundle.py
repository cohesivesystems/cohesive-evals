#!/usr/bin/env python3
"""Emit public contracts for one active checkpoint/probe, independent of condition."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parents[1]
INT_MAX = 2147483647
PROFILES = [(g, None) for g in ('G0', 'G1', 'G2', 'G3')] + [
    (g, p) for g in ('G0', 'G3') for p in ('H', 'L')]


def active_features(checkpoint, probe=None):
    if (checkpoint, probe) not in PROFILES:
        raise ValueError('Use G0–G3; probes are independent and allowed only at G0/G3')
    return [f'E{i}' for i in range(1, int(checkpoint[1])+1)] + ([probe] if probe else [])


def baseline(name):
    conventional = (CASE/'conditions/conventional'/name).read_bytes()
    cohesive = (CASE/'conditions/cohesive'/name).read_bytes()
    if conventional != cohesive:
        raise ValueError('Baseline condition contracts differ: '+name)
    return conventional


def obj(properties, required=None, extra=False):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': extra}


def integer(minimum=0):
    return {'type': 'integer', 'minimum': minimum, 'maximum': INT_MAX}


def documents(checkpoint, probe=None):
    active = active_features(checkpoint, probe)
    profile = '-'.join([checkpoint] + ([probe] if probe else []))
    wire = json.loads(baseline('schemas.json'))
    wire['$id'] = f'https://cohesive.systems/fulfillment/contracts/v1/{profile}/schemas.json'
    defs = wire['$defs']
    identifier = copy.deepcopy(defs['OrderSummary']['properties']['id'])
    statuses = ['Draft', 'Submitted']
    outcomes = defs['Completion']['oneOf'][1]['properties']['outcome']['enum']
    conflicts = ['OrderNotDraft', 'RequestIdentityConflict']
    if 'E1' in active:
        defs['Inventory']['properties']['maxPerOrder'] = integer(1)
        defs['Inventory']['required'].append('maxPerOrder')
        defs['QuantityLimitRequest'] = obj({'maxPerOrder': integer(1)}, extra=True)
        outcomes.append('QuantityLimitExceeded')
    if 'E2' in active:
        statuses.append('Cancelled')
        outcomes.append('OrderCancelled')
        conflicts += ['OrderCancelled', 'OrderNotCancellable']
    if 'E3' in active:
        defs['Inventory']['properties']['quarantined'] = {'type': 'boolean'}
        defs['Inventory']['required'].append('quarantined')
        outcomes.append('InventoryQuarantined')
    if 'H' in active:
        statuses.append('OnHold')
        outcomes.append('OrderOnHold')
        conflicts += ['OrderOnHold', 'OrderNotHoldable', 'OrderHoldNotReleasable']
    for name in ('OrderSummary', 'OrderDetails'):
        defs[name]['properties']['status']['enum'] = statuses.copy()
        if 'L' in active:
            defs[name]['properties']['reviewMarked'] = {'type': 'boolean'}
            defs[name]['required'].append('reviewMarked')
    if 'L' in active:
        defs['Review'] = obj({'id': identifier, 'marked': {'type': 'boolean'}})
    defs['Conflict'] = obj({'code': {'enum': conflicts}}, extra=True)
    defs['ExecutionFailure'] = obj({'code': {'const': 'ExecutionFailed'}}, extra=True)

    seed_inventory = copy.deepcopy(defs['Inventory'])
    seed_inventory['additionalProperties'] = False
    seed_inventory['required'] = ['sku', 'available']
    for name, default in [('maxPerOrder', INT_MAX), ('quarantined', False)]:
        if name in seed_inventory['properties']:
            seed_inventory['properties'][name]['default'] = default
    seed_defs = {
        'Order': obj({'id': identifier, 'status': {'enum': statuses}}),
        'Inventory': seed_inventory,
        'Reservation': obj({'id': identifier, 'orderId': identifier, 'sku': identifier, 'quantity': integer(1)})}
    props = {key: {'type': 'array', 'items': {'$ref': '#/$defs/'+name}}
             for key, name in [('orders', 'Order'), ('inventory', 'Inventory'), ('reservations', 'Reservation')]}
    if 'L' in active:
        seed_defs['Review'] = defs['Review']
        props['reviews'] = {'type': 'array', 'items': {'$ref': '#/$defs/Review'}, 'default': []}
    seed = {'$schema': wire['$schema'],
            '$id': f'https://cohesive.systems/fulfillment/contracts/v1/{profile}/seed.schema.json',
            'title': 'Application provisioning input', **obj(props, ['orders', 'inventory', 'reservations']),
            '$defs': seed_defs,
            '$comment': 'Uniqueness, references and loader defaults are specified in CONTRACT.md.'}

    # Order is contractual, independent of reference process-step order.
    precedence = ['OrderMissing', 'existing reservation match/conflict', 'InventoryMissing', 'InvalidQuantity']
    if 'E3' in active:
        precedence.append('InventoryQuarantined')
    if 'E1' in active:
        precedence.append('QuantityLimitExceeded')
    precedence.append('InsufficientStock')
    if 'H' in active:
        precedence.append('OrderOnHold')
    if 'E2' in active:
        precedence.append('OrderCancelled')
    precedence += ['OrderRejected for any other non-Draft state', 'ReservedAndSubmitted']
    contract = baseline('CONTRACT.md').decode()
    contract += '\n# Active contract supplements\n\nThe sections below extend and supersede the corresponding baseline fields,\nstate tables and setup rules above. All other baseline behavior remains required.\n'
    for feature in active:
        contract += '\n' + (ROOT/'supplements'/f'{feature}.md').read_text()
    contract += '\n## Active fulfillment decision order\n\nExact retained-request replay precedes evaluation. For a new request:\n\n'
    contract += ''.join(f'{i}. {rule}.\n' for i, rule in enumerate(precedence, 1))
    contract += '\nExisting reservation success/conflict and completed-rejection effects retain\nthe baseline definitions. Non-success domain outcomes remain HTTP 200/Rejected.\n'
    setup = (ROOT/'SETUP.md').read_text()
    defaults = []
    if 'E1' in active:
        defaults.append('`maxPerOrder` defaults to 2147483647')
    if 'E3' in active:
        defaults.append('`quarantined` defaults to false')
    active_setup = ('Omitted inventory fields: '+ '; '.join(defaults)+'. Explicit null is invalid.\n') if defaults else ''
    active_setup += 'Only statuses and fields listed in the active seed schema are allowed.\n'
    if 'L' in active:
        active_setup += ('Optional `reviews` defaults to []; each entry is `{id,marked}` referencing\n'
                         'an existing order, with at most one entry per order. Missing records mean\n'
                         'false; explicit null is invalid.\n')
    active_setup += 'Schema defaults describe loader behavior; validation does not insert them.\n\n'
    setup = setup.format(seed_defaults=active_setup.rstrip(),
                         review_persistence=' and review state' if 'L' in active else '')
    contract += '\n' + setup
    examples = []
    for feature in ['G0', *active]:
        examples.extend(json.loads((ROOT/'examples'/f'{feature}.json').read_text()))
    return {'CONTRACT.md': contract,
            'schemas.json': json.dumps(wire, indent=2)+'\n',
            'seed.schema.json': json.dumps(seed, indent=2)+'\n',
            'contract-examples.json': json.dumps(examples, indent=2)+'\n'}


def emit(checkpoint, probe, output):
    contents = documents(checkpoint, probe)
    output.mkdir(parents=True, exist_ok=False)
    for name, content in contents.items():
        (output/name).write_text(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True, choices=['G0', 'G1', 'G2', 'G3'])
    parser.add_argument('--probe', choices=['H', 'L'])
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    emit(args.checkpoint, args.probe, args.output)


if __name__ == '__main__':
    main()
