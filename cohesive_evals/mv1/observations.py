"""Strict MV1 wire observations, shared by adapters without encoding expected business answers."""

from dataclasses import dataclass
from ..contracts import AdapterError


def fields(value, schema):
    """Require exact fields/types; Python's bool-as-int equality must not mask bad evidence."""
    if type(value) is not dict or set(value) != set(schema):
        raise AdapterError("protocol", "Missing or unexpected MV1 observation fields")
    for name, expected in schema.items():
        if type(value[name]) is not expected:
            raise AdapterError("protocol", f"Invalid MV1 field type: {name}")
        if expected is int and not -(2**31) <= value[name] <= 2**31 - 1:
            raise AdapterError("protocol", f"Out-of-range MV1 Int32: {name}")


@dataclass(frozen=True)
class InventoryObservation:
    """Observed inventory state, not a predicted or model-derived expectation."""

    Sku: str
    Available: int
    MaxPerOrder: int
    Quarantined: bool

    @classmethod
    def read(cls, value):
        """Decode exact JSON types and reject malformed state before business grading."""
        fields(
            value,
            {"Sku": str, "Available": int, "MaxPerOrder": int, "Quarantined": bool},
        )
        return cls(**value)


@dataclass(frozen=True)
class Observation:
    """Framework-neutral outcome/state from one requested offline case."""

    Name: str
    Outcome: str
    FulfillmentOutcome: str
    After: InventoryObservation
    ScopePreserved: bool

    @classmethod
    def read(cls, value):
        """Decode shape only; unknown outcome strings remain independently testable behavior."""
        fields(
            value,
            {
                "Name": str,
                "Outcome": str,
                "FulfillmentOutcome": str,
                "After": dict,
                "ScopePreserved": bool,
            },
        )
        return cls(**{**value, "After": InventoryObservation.read(value["After"])})


def validate(results):
    """Validate every returned observation, keeping unavailable evidence unqualified."""
    if type(results) is not list:
        raise AdapterError("protocol", "MV1 results must be an array")
    return [Observation.read(result) for result in results]
