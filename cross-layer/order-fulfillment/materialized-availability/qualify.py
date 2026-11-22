"""Qualify both built references and six built controls, retaining independent G0 evidence."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from build import BASE, CASE, CONDITIONS, build_tools
from cohesive_evals.evidence import dump
from cohesive_evals.qualification import classify
from verify import RequirementFailure, check


def qualify(references, controls, output):
    """Require both known-good runs, exact mutant detections and matching G0 observations."""
    output.mkdir(parents=True, exist_ok=False)
    summary = {"baseline": BASE, "conditions": {}, "passed": False}
    for condition in CONDITIONS:
        folder = references / condition
        good = output / condition
        check(folder, good, condition)
        result = json.loads((good / "report.json").read_text())
        record = result["conditions"][condition]
        summary["conditions"][condition] = record
        summary["postgresImageId"] = result["postgresImageId"]
        record["controls"] = {}
        for defect, (root, assertion) in controls.items():
            candidate = root / condition
            target = output / f"{condition}-{defect}"
            outcome = classify(lambda: check(candidate, target, condition), RequirementFailure, assertion)
            record["controls"][defect] = outcome
            dump(output / "qualification.json", summary)
            if outcome["kind"] != "detected":
                raise RuntimeError(f"{condition}/{defect}: {outcome}")
            outcome["buildManifestSha256"] = build_tools.verify_build(candidate)

    retained = output / "g0"
    subprocess.run([sys.executable, str(CASE / "verification/verify.py"), "--fixtures", str(references),
                    "--output", str(retained)], check=True)
    report = json.loads((retained / "report.json").read_text())
    summary["g0"] = {key: report[key] for key in
        ("passed", "pairEquivalenceChecked", "checksPerCondition", "invariantCommandsPerCondition",
         "sdk", "cohesiveSourceRevision")}
    summary["passed"] = report["passed"] and report["pairEquivalenceChecked"]
    dump(output / "qualification.json", summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("references", "stale_stock", "live_read", "resync_noop", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    qualify(args.references.resolve(), {"stale-stock": (args.stale_stock.resolve(), "shared-sku-fanout"),
            "live-read": (args.live_read.resolve(), "projection-only-read"),
            "resync-noop": (args.resync_noop.resolve(), "explicit-resync")}, args.output.resolve())
