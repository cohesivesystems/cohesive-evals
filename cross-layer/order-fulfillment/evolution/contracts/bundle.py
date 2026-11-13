#!/usr/bin/env python3
"""Emit public contracts for one active checkpoint/probe, independent of condition."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parents[1]
INT_MAX = 2147483647
MANIFEST = json.loads((ROOT/'features.json').read_text())
PROFILES = [(g, None) for g in MANIFEST['checkpoints']] + [
    (g, p) for g in MANIFEST['checkpoints'] for p, checkpoints in MANIFEST['probes'].items()
    if g in checkpoints]


def active_features(checkpoint, probe=None):
    if (checkpoint, probe) not in PROFILES:
        raise ValueError('Unsupported checkpoint/probe combination')
    return MANIFEST['checkpoints'][checkpoint].copy() + ([probe] if probe else [])


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
    inventory_defaults = {}
    seed_resources = {}
    setup_text = ''
    persistence_text = ''
    for feature in active:
        addition = MANIFEST['features'][feature]
        for name, properties in addition.get('properties', {}).items():
            defs[name]['properties'].update(copy.deepcopy(properties))
            defs[name]['required'].extend(properties)
        defs.update(copy.deepcopy(addition.get('definitions', {})))
        statuses.extend(addition.get('statuses', []))
        outcomes.extend(addition.get('outcomes', []))
        conflicts.extend(addition.get('conflicts', []))
        inventory_defaults.update(addition.get('inventoryDefaults', {}))
        seed_resources.update(addition.get('seedResources', {}))
        setup_text += addition.get('setupText', '')
        persistence_text += addition.get('persistenceText', '')
    for name in ('OrderSummary', 'OrderDetails'):
        defs[name]['properties']['status']['enum'] = statuses.copy()
    defs['Conflict'] = obj({'code': {'enum': conflicts}}, extra=True)
    defs['ExecutionFailure'] = obj({'code': {'const': 'ExecutionFailed'}}, extra=True)

    seed_inventory = copy.deepcopy(defs['Inventory'])
    seed_inventory['additionalProperties'] = False
    seed_inventory['required'] = ['sku', 'available']
    for name, default in inventory_defaults.items():
        seed_inventory['properties'][name]['default'] = default
    seed_defs = {
        'Order': obj({'id': identifier, 'status': {'enum': statuses}}),
        'Inventory': seed_inventory,
        'Reservation': obj({'id': identifier, 'orderId': identifier, 'sku': identifier, 'quantity': integer(1)})}
    props = {key: {'type': 'array', 'items': {'$ref': '#/$defs/'+name}}
             for key, name in [('orders', 'Order'), ('inventory', 'Inventory'), ('reservations', 'Reservation')]}
    for name, resource in seed_resources.items():
        definition = resource['definition']
        seed_defs[definition] = copy.deepcopy(defs[definition])
        props[name] = {'type': 'array', 'items': {'$ref': '#/$defs/'+definition},
                       'default': resource['default']}
    seed = {'$schema': wire['$schema'],
            '$id': f'https://cohesive.systems/fulfillment/contracts/v1/{profile}/seed.schema.json',
            'title': 'Application provisioning input', **obj(props, ['orders', 'inventory', 'reservations']),
            '$defs': seed_defs,
            '$comment': 'Uniqueness, references and loader defaults are specified in CONTRACT.md.'}

    # Order is contractual, independent of reference process-step order.
    precedence = [entry['rule'] for entry in MANIFEST['precedence']
                  if 'feature' not in entry or entry['feature'] in active]
    contract = baseline('CONTRACT.md').decode()
    contract += '\n# Active contract supplements\n\nThe sections below extend and supersede the corresponding baseline fields,\nstate tables and setup rules above. All other baseline behavior remains required.\n'
    for feature in active:
        contract += '\n' + (ROOT/'supplements'/f'{feature}.md').read_text()
    contract += '\n## Active fulfillment decision order\n\nExact retained-request replay precedes evaluation. For a new request:\n\n'
    contract += ''.join(f'{i}. {rule}.\n' for i, rule in enumerate(precedence, 1))
    contract += '\nExisting reservation success/conflict and completed-rejection effects retain\nthe baseline definitions. Non-success domain outcomes remain HTTP 200/Rejected.\n'
    setup = (ROOT/'SETUP.md').read_text()
    defaults = [f'`{name}` defaults to {json.dumps(value)}'
                for name, value in inventory_defaults.items()]
    active_setup = ('Omitted inventory fields: '+ '; '.join(defaults)+'. Explicit null is invalid.\n') if defaults else ''
    active_setup += 'Only statuses and fields listed in the active seed schema are allowed.\n'
    active_setup += setup_text
    active_setup += 'Schema defaults describe loader behavior; validation does not insert them.\n\n'
    setup = setup.format(seed_defaults=active_setup.rstrip(),
                         review_persistence=persistence_text)
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
    parser.add_argument('--checkpoint', required=True, choices=list(MANIFEST['checkpoints']))
    parser.add_argument('--probe', choices=list(MANIFEST['probes']))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    emit(args.checkpoint, args.probe, args.output)


if __name__ == '__main__':
    main()
