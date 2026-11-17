"""Exact named-assertion credit shared without importing scenario expectations."""

from .contracts import AdapterError


def failure(error: Exception) -> dict:
    """Represent unavailable evidence separately from a detected application defect."""
    return {
        "kind": "unqualified",
        "category": (
            error.category if isinstance(error, AdapterError) else "infrastructure"
        ),
        "detail": repr(error),
    }


def classify(check, behavioral_failure, assertion: str) -> dict:
    """Run an independent check; credit only the specified named business assertion."""
    try:
        check()
    except behavioral_failure as error:
        return {
            "kind": "detected" if error.assertion == assertion else "wrong-assertion",
            "assertion": error.assertion,
            "detail": str(error),
        }
    except Exception as error:
        return failure(error)
    return {"kind": "survived"}
