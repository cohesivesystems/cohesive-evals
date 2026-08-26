# Private oracle

This directory contains maintainer-only oracle design, hidden fixtures,
executable checks, obligation mappings, and oracle-qualification patches.

The Load Search Mapping design gate is approved. Its behavioral allocation,
treatment-integrity rules, and qualification cases are documented in
[`load-search-mapping/obligations.md`](load-search-mapping/obligations.md). The
executable scorer and its qualification package live beside that document.

The candidate oracle is fully qualified against both known-correct solutions,
both unchanged baselines, per-condition defects for every behavioral check,
contract and visible-test gate failures, and condition-specific integrity
bypasses. It cannot be frozen until the independent conventional baseline
review in COH-59 is complete.

Nothing under this directory may be copied into an evaluated agent workspace.
The runner will attach it only in a separate post-run scoring workspace.
