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
        declaration = '[property: System.ComponentModel.DataAnnotations.MaxLength(64)] '
        cases.update({
            'declaration-removed': ('Contracts.cs', declaration, '', 'PV2-01', 'length boundary'),
            'declaration-63': ('Contracts.cs', 'MaxLength(64)', 'MaxLength(63)', 'PV2-01', 'length boundary'),
            'declaration-65': ('Contracts.cs', 'MaxLength(64)', 'MaxLength(65)', 'PV2-01', 'length boundary'),
            'projection-disabled': ('FulfillmentInput.cs', '.UseDataAnnotations()', '', 'PV2-01', 'length boundary'),
            'stale-validation-input': ('FulfillmentInput.cs', 'ValidateInput(request, Inputs)', 'ValidateInput(request with { RequestId = "cached-valid" }, Inputs)', 'PV2-01', 'length boundary'),
            'validation-bypassed': ('FulfillmentInput.cs', 'ObservationValidator.ValidateInput(request, Inputs).IsValid', 'true', 'PV2-01', 'length boundary'),
        })
    return cases
