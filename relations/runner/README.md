# Evaluation runner

This directory is reserved for validation, isolated execution, scoring, and
reporting code. The runner is deliberately deferred until the protocol, matched
baselines, and oracle have been reviewed and validated.

`dotnet test` is expected to execute checks; the runner will control the
experiment, preserve evidence, and map check results to obligations.
