"""Build the worker overlays on verified, pinned synchronous fixtures."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "materialized-availability"))
from build import APP, CONDITIONS, build_tools
from cohesive_evals.snapshots import apply_delta


DEFECTS = {"eager": "stale-while-paused", "late-publication": "published-before-ack",
           "over-acknowledge": "checkpoint-captured-cut"}


def mutate(candidate, defect):
    """Introduce one scoped timing defect and reject changed or ambiguous mutation anchors."""
    queue = candidate / APP / "OperationQueue.cs"
    worker = candidate / APP / "AvailabilityMaintenance.cs"
    publish = "            await projection.Refresh();"
    ack = "cmd.Parameters.AddWithValue(cut.Requested);\n            await cmd.ExecuteNonQueryAsync();"
    if defect == "eager":
        path = queue
        anchor = "                    lock (gate) entry.Result = result;"
        changes = [(anchor, "                    await backend.Availability.Refresh();\n" + anchor)]
    elif defect == "late-publication":
        path = worker
        changes = [(publish, ""), (ack, ack + "\n" + publish)]
    elif defect == "over-acknowledge":
        path = worker
        second = ('cmd.CommandText = "UPDATE availability_progress SET revision = '
                  '(SELECT revision FROM availability_request)";\n            cmd.Parameters.Clear();\n'
                  '            await cmd.ExecuteNonQueryAsync();')
        anchor = "cmd.Parameters.AddWithValue(cut.Requested);\n            await cmd.ExecuteNonQueryAsync();"
        changes = [(anchor, anchor + "\n            " + second)]
    else:
        raise ValueError(f"Unknown defect {defect}")
    text = path.read_text()
    for before, after in changes:
        if text.count(before) != 1:
            raise ValueError(f"Ambiguous {defect} mutation in {path}")
        text = text.replace(before, after)
    path.write_text(text)


def build(baseline, output, defect=None):
    """Verify the full baseline input set before applying each checked condition delta."""
    pins = json.loads((ROOT / "pins.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    for condition in CONDITIONS:
        original = baseline / condition
        build_tools.verify_build(original)
        inputs = build_tools.input_hashes(original)
        digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        if pins["inputSha256"][condition] != digest:
            raise ValueError(f"Unexpected synchronous inputs for {condition}")
        candidate = output / condition
        shutil.copytree(original, candidate, ignore=shutil.ignore_patterns("bin", "obj", "build.log", "build-manifest.json"))
        reference = ROOT / "reference" / "host"
        apply_delta(candidate, reference.with_suffix(".patch"), reference.with_suffix(".json"))
        shutil.copyfile(reference.parent / "AvailabilityMaintenance.cs", candidate / APP / "AvailabilityMaintenance.cs")
        shutil.copyfile(reference.parent / f"{condition}.cs", candidate / APP / "AvailabilitySources.cs")
        if defect:
            mutate(candidate, defect)
        with (candidate / "build.log").open("w") as log:
            build_tools.build_candidate(candidate, log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--defect", choices=DEFECTS)
    args = parser.parse_args()
    build(args.baseline.resolve(), args.output.resolve(), args.defect)
