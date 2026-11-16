"""Named defects prove declaration-driven enforcement, not a duplicated length predicate."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pv2.mutations import mutations as previous

def mutations(condition):
    cases = previous(condition)
    if condition == 'cohesive':
        for name in ('stale-validator', 'reject-64', 'accept-65', 'grapheme-counting'):
            del cases[name]
        for name, mutation in list(cases.items()):
            file, before, after, obligation, assertion = mutation
            cases[name] = (file, before.replace('FulfillmentInput.IsValid(request)', 'inputs.Validate(request).IsValid'),
                           after.replace('FulfillmentInput.IsValid(request)', 'inputs.Validate(request).IsValid'), obligation, assertion)
        cases.update({
            'declaration-removed': ('Contracts.cs', 'Required, MaxLength(64)', 'Required', 'PV2-01', 'length boundary'),
            'declaration-63': ('Contracts.cs', 'MaxLength(64)', 'MaxLength(63)', 'PV2-01', 'length boundary'),
            'declaration-65': ('Contracts.cs', 'MaxLength(64)', 'MaxLength(65)', 'PV2-01', 'length boundary'),
            'projection-disabled': ('Program.cs', '.UseDataAnnotations()', '', 'PV2-01', 'length boundary'),
            'stale-validation-input': ('OperationQueue.cs', 'inputs.Validate(request)', 'inputs.Validate(request with { RequestId = "cached-valid" })', 'PV2-01', 'length boundary'),
            'validation-bypassed': ('OperationQueue.cs', 'inputs.Validate(request).IsValid', '(inputs is not null)', 'PV2-01', 'length boundary'),
            'required-request-removed': ('Contracts.cs', 'Required, MaxLength(64)', 'MaxLength(64)', 'PV2-01', 'length boundary'),
            'required-order-removed': ('Contracts.cs', '[property: Required] string OrderId', 'string OrderId', 'TI-01', 'required input'),
            'required-sku-removed': ('Contracts.cs', '[property: Required] string Sku', 'string Sku', 'TI-01', 'required input'),
        })
    return cases
