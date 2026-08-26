# Private oracle

This directory contains maintainer-only oracle design, hidden fixtures,
executable checks, obligation mappings, and oracle-qualification patches.

The Load Search Mapping oracle is currently at its obligation review gate. Its
proposed behavioral checks, treatment-integrity checks, and qualification cases
are documented in
[`load-search-mapping/obligations.md`](load-search-mapping/obligations.md).
Executable hidden checks must not be implemented until that review is accepted.

Nothing under this directory may be copied into an evaluated agent workspace.
The runner will attach it only in a separate post-run scoring workspace.
