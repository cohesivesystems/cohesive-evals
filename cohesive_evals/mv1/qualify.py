#!/usr/bin/env python3
"""Post-freeze maintainer qualification, not a blinded participant experiment."""
from dataclasses import asdict
import json
from pathlib import Path

from . import fixture, oracle
from .defects import defects, apply
from .paths import EVALUATION as ROOT
from ..qualification import classify as classify_check, failure


from ..evidence import dump


def check_freeze(frozen):
    """Reject drift in frozen source, generated suites, production inputs or adapter binaries."""
    recorded = json.loads((ROOT / "suite-freeze.json").read_text())
    actual = fixture.source_hashes()
    if actual != recorded["sources"]:
        raise ValueError("Frozen suite source changed")
    run_freeze = json.loads((frozen / "freeze.json").read_text())
    if run_freeze["sources"] != recorded["sources"]:
        raise ValueError("Reference run uses a different suite source freeze")
    # A reproduction has its own build paths/output hashes; retain that run's identity.
    recorded = run_freeze
    for version in fixture.VERSIONS:
        for condition in fixture.CONDITIONS:
            folder = frozen / version / "suites" / condition
            expected = recorded["references"][version][condition]
            for file, key in [
                ("suite.json", "suiteSha256"),
                ("manifest.json", "manifestSha256"),
            ]:
                if fixture.sha(folder / file) != expected[key]:
                    raise ValueError("Frozen reference changed: " + str(folder / file))
            manifest = json.loads((folder / "manifest.json").read_text())
            for file, digest in manifest["outputs"].items():
                if fixture.sha(folder / file) != digest:
                    raise ValueError("Frozen adapter output changed: " + file)
            if (
                fixture.adapter(condition).observe(
                    frozen / version / "references" / condition
                )
                != manifest["production"]
            ):
                raise ValueError("Production reference changed")
    return recorded


def classify(cases, results, version, assertion):
    """Credit only the expected behavioral assertion; distinguish survival and invalid runs."""
    return classify_check(
        lambda: oracle.check(cases, results, version),
        oracle.BehavioralFailure,
        assertion,
    )


def require_model(expected, actual):
    """Reject evidence referring to any different definition, revision or fingerprint."""
    if expected != actual:
        raise ValueError(
            "Model authority mismatch: expected exact definition/revision/fingerprint"
        )


def controls(frozen):
    """Rerun correct references and challenge stale authority and unsupported generation."""
    records = {}
    for version in fixture.VERSIONS:
        for condition in fixture.CONDITIONS:
            folder = frozen / version / "suites" / condition
            cases = json.loads((folder / "suite.json").read_text())["cases"]
            # Re-execute correct controls, rather than trusting their recorded success.
            temporary = folder / "qualification-inputs.json"
            dump(temporary, cases)
            results = fixture.invoke(frozen / version, condition, temporary)
            records[version + "/" + condition] = oracle.check(cases, results, version)
    # Stale model metadata cannot be substituted for another policy revision.
    original = json.loads((frozen / "original/suites/cohesive/suite.json").read_text())[
        "modelReference"
    ]
    revised = json.loads((frozen / "revised/suites/cohesive/suite.json").read_text())[
        "modelReference"
    ]
    for version, expected in [("original", original), ("revised", revised)]:
        actual = fixture.invoke(frozen / version, "cohesive", "--describe")["metadata"]
        require_model(expected, {k: actual[k] for k in expected})
    try:
        require_model(original, revised)
    except ValueError:
        pass
    else:
        raise AssertionError("Stale model authority accepted")
    records["staleModel"] = {
        "kind": "identity-mismatch",
        "original": original,
        "revised": revised,
    }
    result = fixture.invoke(frozen / "original", "cohesive", "--unsupported-control")
    if result.get("kind") != "unsupported":
        raise AssertionError("Unsupported predicate was silently accepted")
    records["unsupportedNode"] = result
    return records


def run(frozen, output):
    """Build each production fault and classify it against the frozen independent suite."""
    output.mkdir(parents=True, exist_ok=False)
    try:
        check_freeze(frozen)
        manifest = {c: [asdict(d) for d in defects(c)] for c in fixture.CONDITIONS}
        # Persist evaluator manifest before any defect is built or run.
        dump(output / "defect-manifest.json", manifest)
        baseline = controls(frozen)
        records = []
        for version in fixture.VERSIONS:
            for condition in fixture.CONDITIONS:
                cases = json.loads(
                    (frozen / version / "suites" / condition / "suite.json").read_text()
                )["cases"]
                for defect in defects(condition):
                    work = output / version / condition / defect.name
                    record = {
                        "version": version,
                        "condition": condition,
                        "defect": defect.name,
                        "expectedAssertion": defect.assertion,
                    }
                    try:
                        fixture.materialize(work, version)
                        apply(work / "references" / condition, defect)
                        fixture.compile_adapter(work, condition)
                        folder = work / "suites" / condition
                        dump(folder / "cases.json", cases)
                        results = fixture.invoke(work, condition, folder / "cases.json")
                        dump(folder / "results.json", results)
                        record.update(
                            classify(cases, results, version, defect.assertion)
                        )
                        record["manifestSha256"] = fixture.sha(folder / "manifest.json")
                        # A missing model guard must not erase independent requirements.
                        if condition == "cohesive" and defect.name in (
                            "zero-admitted",
                            "quarantine-omitted",
                        ):
                            suite = fixture.invoke(work, condition, "--generate")
                            dump(folder / "correlated-suite.json", suite)
                            dump(folder / "correlated-inputs.json", suite["cases"])
                            actual = fixture.invoke(
                                work, condition, folder / "correlated-inputs.json"
                            )
                            independent = classify(
                                suite["cases"], actual, version, "domain outcome"
                            )
                            if independent["kind"] != "detected":
                                raise AssertionError(
                                    "Wrong model escaped independent assertions"
                                )
                            record["correlatedModelControl"] = {
                                **independent,
                                "cases": len(suite["cases"]),
                                "modelReference": suite["modelReference"],
                                "misleadingSelfAgreement": {
                                    "matches": len(actual),
                                    "meaning": "Copying candidate outputs as expectations agrees by construction; grants no correctness credit",
                                },
                            }
                    except Exception as error:
                        record.update(failure(error))
                    work.mkdir(parents=True, exist_ok=True)
                    dump(work / "qualification.json", record)
                    records.append(record)
                    print(version, condition, defect.name, record["kind"], flush=True)
        check_freeze(frozen)
        report = {
            "passed": all(r["kind"] == "detected" for r in records),
            "design": "post-freeze maintainer qualification; not blinded or held-out from the author",
            "freezeSha256": fixture.sha(ROOT / "suite-freeze.json"),
            "referenceRunFreezeSha256": fixture.sha(frozen / "freeze.json"),
            "defectManifestSha256": fixture.sha(output / "defect-manifest.json"),
            "controls": baseline,
            "records": records,
        }
        dump(output / "report.json", report)
        if not report["passed"]:
            raise RuntimeError(
                "Qualification incomplete; inspect per-case classifications"
            )
    except Exception as error:
        dump(output / "failure.json", {"kind": "unqualified", "detail": repr(error)})
        raise
