#!/usr/bin/env python3
"""Build the two versioned references, freeze generated cases, then independently check them."""
import hashlib
import json
from pathlib import Path
from . import fixture, oracle


from ..evidence import dump


def run(output, prepare_locks=False):
    """Build both policies, generate and verify typed cases, then freeze their provenance."""
    output.mkdir(parents=True, exist_ok=False)
    records = {}
    for version in fixture.VERSIONS:
        work = output / version
        fixture.materialize(work, version)
        records[version] = {}
        for condition in fixture.CONDITIONS:
            manifest = fixture.compile_adapter(work, condition, prepare_locks)
            document = (
                fixture.invoke(work, condition, "--describe")
                if condition == "cohesive"
                else None
            )
            if document:
                dump(work / "transition.json", document)
            suite = fixture.invoke(work, condition, "--generate")
            suite.update(
                condition=condition,
                policy=version,
                scope="bounded cases; not exhaustive Int32 verification",
            )
            folder = work / "suites" / condition
            dump(folder / "suite.json", suite)
            dump(folder / "cases.json", suite["cases"])
            results = fixture.invoke(work, condition, folder / "cases.json")
            dump(folder / "results.json", results)
            checked = oracle.check(suite["cases"], results, version)
            records[version][condition] = {
                **checked,
                "suiteSha256": fixture.sha(folder / "suite.json"),
                "manifestSha256": fixture.sha(folder / "manifest.json"),
            }

        # Matched inputs are verified, not assumed from shared formatting helpers.
        def read(c):
            """Read a condition catalog for exact cross-condition input comparison."""
            return json.loads((work / "suites" / c / "suite.json").read_text())["cases"]

        if read("cohesive") != read("conventional"):
            raise AssertionError("Different matched inputs")
    # A stale initial-policy suite must detect the supplied maintenance change in both conditions.
    maintenance = {}
    for c in fixture.CONDITIONS:
        folder = output / "revised/suites" / c
        cases = json.loads((output / "original/suites" / c / "cases.json").read_text())
        results = json.loads((folder / "results.json").read_text())
        if cases != json.loads((folder / "cases.json").read_text()):
            raise AssertionError("Maintenance input drift")
        try:
            oracle.check(cases, results, "original")
        except oracle.BehavioralFailure as error:
            if error.assertion != "domain outcome":
                raise
            maintenance[c] = {"assertion": error.assertion, "detail": str(error)}
        else:
            raise AssertionError("Stale policy suite did not fail")
    # Freeze before evaluator fault injection. No elapsed-time or blinded trial claims.
    sources = fixture.source_hashes()
    dump(output / "freeze.json", {"sources": sources, "references": records})
    dump(
        output / "report.json",
        {
            "passed": True,
            "conditions": records,
            "stalePolicyControls": maintenance,
            "freezeSha256": fixture.sha(output / "freeze.json"),
        },
    )
    print(
        "MV1 references passed; suite freeze:",
        fixture.sha(output / "freeze.json"),
        flush=True,
    )
