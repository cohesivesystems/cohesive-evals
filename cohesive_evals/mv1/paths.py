"""Locate versioned scenario assets in the repository checkout."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CASE = REPO / "cross-layer/order-fulfillment"
ROOT = CASE / "probes/model-verification"
SUITES = ROOT / "suites"
EVALUATION = ROOT / "evaluation"
SDK = ROOT / "sdk"
CONDITIONS = ("conventional", "cohesive")
VERSIONS = ("original", "revised")
