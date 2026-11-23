"""Collect passing worker traces and credit only the named assertion for each deliberate defect."""

import argparse
import json
from pathlib import Path

from build_async import CONDITIONS, DEFECTS
from verify_async import RequirementFailure, check, dump
from cohesive_evals.qualification import classify


def qualify(references, controls, output):
    """Run both conditions independently and preserve each outcome before advancing."""
    output.mkdir(parents=True, exist_ok=False)
    summary = {"passed": False, "conditions": {}}
    for condition in CONDITIONS:
        good = output / condition
        check(references / condition, good, condition)
        result = json.loads((good / "report.json").read_text())
        record = result["conditions"][condition]
        summary["conditions"][condition] = record
        summary["postgresImageId"] = result["postgresImageId"]
        record["controls"] = {}
        for defect, assertion in DEFECTS.items():
            target = controls / defect / condition
            observed = classify(lambda: check(target, output / f"{condition}-{defect}", condition),
                                RequirementFailure, assertion)
            record["controls"][defect] = observed
            dump(output / "qualification.json", summary)
            if observed["kind"] != "detected":
                raise RuntimeError(f"{condition}/{defect}: {observed}")
    summary["passed"] = True
    dump(output / "qualification.json", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("references", "controls", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    qualify(args.references.resolve(), args.controls.resolve(), args.output.resolve())
