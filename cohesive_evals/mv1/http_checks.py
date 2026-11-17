"""Independent MV1 HTTP requirements, retained from the qualified public-contract checks."""

import json


class BehavioralFailure(AssertionError):
    """A named public behavior failure, distinct from unavailable observations."""

    def __init__(self, obligation, assertion, detail):
        """Retain requirement identity and diagnostic detail."""
        self.obligation, self.assertion = obligation, assertion
        super().__init__(str(detail))


def require(ok, obligation, assertion, detail):
    """Raise only a named business assertion, never an execution error."""
    if not ok:
        raise BehavioralFailure(obligation, assertion, detail)


def canonical(facts):
    """Normalize database row order without discarding fields or identities."""
    return {
        k: sorted(v, key=lambda x: json.dumps(x, sort_keys=True))
        for k, v in facts.items()
    }


class Checks:
    """Independent public outcome, replay and physical-state assertions."""

    def __init__(self, world):
        """Start a trace and assertion counters for one independently seeded host."""
        self.world = world
        self.trace = []
        self.expected = None
        self.counts = {}

    def check(self, ok, number, name, detail):
        """Record a successful requirement check or raise its named failure."""
        require(ok, "MV1-" + number, name, detail)
        self.counts[name] = self.counts.get(name, 0) + 1

    def call(self, method, path, body=None, raw=None):
        """Record HTTP observations; server errors cannot count as business evidence."""
        status, value = self.world.client.request(method, path, body, raw)
        self.trace.append(dict(method=method, path=path, status=status, body=value))
        if status >= 500:
            raise RuntimeError(("application failure", status, value))
        if path == "/fulfillment/batch" and isinstance(value, dict):
            for item in value.get("items", []):
                if not isinstance(item, dict):
                    continue
                for phase in ("admission", "completion"):
                    reply = item.get(phase)
                    if isinstance(reply, dict) and reply.get("status", 0) >= 500:
                        raise RuntimeError(("batch " + phase + " failure", item))
        return status, value

    def unchanged(self, number, name):
        """Compare all observed facts with independently maintained expectations."""
        facts = self.world.facts()
        self.trace.append({"facts": facts})
        self.check(canonical(facts) == canonical(self.expected), number, name, facts)

    def items(self, mode, requests, outcome, number, name):
        """Check equivalent single/batch admissions and completions against explicit outcomes."""
        if mode == "batch":
            status, result = self.call("POST", "/fulfillment/batch", requests)
            self.check(
                status == 200 and isinstance(result, dict) and "items" in result,
                number,
                name,
                result,
            )
            items = result["items"]
        else:
            items = []
            for i, intent in enumerate(requests):
                status, receipt = self.call("POST", "/fulfillment", intent)
                self.check(status == 202, number, name, (status, receipt))

                def done():
                    """Poll the public receipt URL until a terminal HTTP observation."""
                    reply = self.call("GET", receipt["resultUrl"])
                    return reply if reply[0] != 202 else None

                status, result = self.world.wait(done, "AO1 completion")
                items.append(
                    dict(
                        index=i,
                        admission=dict(status=202, body=receipt),
                        completion=dict(status=status, body=result),
                    )
                )
        self.check(len(items) == len(requests), number, name, items)
        for i, (item, expected) in enumerate(zip(items, outcome)):
            self.check(
                item.get("index") == i
                and item.get("admission", {}).get("status") == 202,
                number,
                name,
                item,
            )
            status = "Submitted" if expected == "ReservedAndSubmitted" else "Rejected"
            self.check(
                item.get("completion")
                == dict(status=200, body=dict(status=status, outcome=expected)),
                number,
                name,
                item,
            )
        return items
