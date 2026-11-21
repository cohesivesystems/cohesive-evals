"""Build isolated availability references or one-defect controls from the pinned G0 tree."""

import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile

from cohesive_evals.snapshots import apply_delta

ROOT = Path(__file__).resolve().parent
CASE = ROOT.parent
BASE = "2e57e3c50e97123fc9f36b428b23bfbfe03b5549"
CONDITIONS = ("conventional", "cohesive")
APP = Path("src/Fulfillment.Application")
spec = importlib.util.spec_from_file_location("durability_build", CASE / "durability/build.py")
build_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_tools)


def materialize(output, defect):
    """Export the trusted Git revision, dereference fixture test links, and apply checked deltas."""
    output.mkdir(parents=True, exist_ok=False)
    relative = CASE.relative_to(CASE.parents[1]) / "conditions"
    with tempfile.TemporaryDirectory() as temporary:
        tree = Path(temporary)
        archive = tree / "inputs.tar"
        subprocess.run(["git", "archive", BASE, "-o", archive, "--", relative, "cohesive_evals"],
                       cwd=CASE.parents[1], check=True)
        subprocess.run(["tar", "-xf", archive, "-C", tree], check=True)
        for condition in CONDITIONS:
            folder = output / condition
            shutil.copytree(tree / relative / condition, folder)
            reference = ROOT / "reference" / condition
            apply_delta(folder, reference.with_suffix(".patch"), reference.with_suffix(".json"))
            shutil.copyfile(reference.with_suffix(".cs"), folder / APP / "AvailabilityProjection.cs")
            if defect == "stale-stock":
                # Suppress the settlement refresh. A's previously persisted X row stays stale.
                queue = folder / APP / "OperationQueue.cs"
                anchor = "finally { await backend.Availability.Refresh(); }"
                source = queue.read_text()
                if source.count(anchor) != 1:
                    raise ValueError("Settlement refresh mutation anchor changed")
                queue.write_text(source.replace(anchor, "finally { }"))
            elif defect == "live-read":
                # Restore just the baseline GET. The backing projection still receives every update.
                program = folder / APP / "Program.cs"
                old = (tree / relative / condition / APP / "Program.cs").read_text()
                start = 'app.MapGet("/orders/{id}/availability"'
                end = 'app.MapPost("/fulfillment"'
                source = program.read_text()
                if any(text.count(anchor) != 1 for text in (old, source) for anchor in (start, end)):
                    raise ValueError("Availability route mutation anchors changed")
                original_route = old[old.index(start):old.index(end)]
                program.write_text(source[:source.index(start)] + original_route + source[source.index(end):])
            with (folder / "build.log").open("w") as log:
                build_tools.build_candidate(folder, log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--defect", choices=["stale-stock", "live-read"])
    args = parser.parse_args()
    materialize(args.output.resolve(), args.defect)
