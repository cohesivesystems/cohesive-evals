"""Independent requirement oracle: no candidate, schema, model or generator imports."""

from .observations import validate


class BehavioralFailure(AssertionError):
    """A named business assertion failure, distinct from infrastructure errors."""

    def __init__(self, assertion, detail):
        """Retain the assertion identity so qualification cannot credit an unrelated failure."""
        self.assertion = assertion
        super().__init__(str(detail))


def expected(case, policy):
    """Compute the required outcome solely from the independent versioned policy."""
    if policy not in ("original", "revised"):
        raise ValueError(policy)
    quantity, stock, limit = case["Quantity"], case["Available"], case["MaxPerOrder"]
    if quantity <= 0:
        return "InvalidQuantity"
    # The specification versions this precedence explicitly, independently of implementation order.
    if policy == "revised" and quantity > limit:
        return "QuantityLimitExceeded"
    if case["Quarantined"]:
        return "InventoryQuarantined"
    if quantity > limit:
        return "QuantityLimitExceeded"
    if quantity > stock:
        return "InsufficientStock"
    return "Reserved"


def check(cases, results, policy):
    """Check every requested case, full state and terminal outcome; return coverage counts."""
    validate(results)
    if len(results) != len(cases):
        raise BehavioralFailure("complete case results", len(results))
    for case, result in zip(cases, results):
        if result["Name"] != case["Name"]:
            raise BehavioralFailure("case identity", result)
        outcome = expected(case, policy)
        if result["Outcome"] != outcome:
            raise BehavioralFailure(
                "domain outcome", {"input": case, "expected": outcome, "actual": result}
            )
        terminal = "ReservedAndSubmitted" if outcome == "Reserved" else outcome
        if result["FulfillmentOutcome"] != terminal:
            raise BehavioralFailure(
                "terminal outcome", {"input": case, "actual": result}
            )
        after = dict(
            Sku=case["Sku"],
            Available=case["Available"]
            - (case["Quantity"] if outcome == "Reserved" else 0),
            MaxPerOrder=case["MaxPerOrder"],
            Quarantined=case["Quarantined"],
        )
        if result["After"] != after or result["ScopePreserved"] is not True:
            raise BehavioralFailure(
                "accepted delta" if outcome == "Reserved" else "rejection preservation",
                {"input": case, "expected": after, "actual": result},
            )
    return {
        "cases": len(cases),
        "accepted": sum(expected(c, policy) == "Reserved" for c in cases),
        "outcomes": sorted({expected(c, policy) for c in cases}),
    }
