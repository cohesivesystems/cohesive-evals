# Python evaluation runner

This is the candidate local runner/scorer foundation for COH-62. Relations is its
regression fixture; cross-layer snapshot chains, cumulative evaluator integration,
H/L conversation isolation and participant packaging are separate follow-up work.
It replays patches without launching a model. Calibration, freeze, production
agent driving and campaign execution are outside this issue. COH-59's independent
conventional review is complete; that does not authorize those deferred actions.

## Run a dry submission

Python 3.9+, Git and the pinned fixture's .NET SDK are required. Runtime code uses
the Python standard library; jq, ripgrep and tar executables are no longer required.
From the repository root:

```sh
python3 -B relations/runner/run.py \
  --condition conventional --run-id example-baseline \
  --output-root /private/tmp/cohesive-eval-runs

python3 -B relations/runner/run.py \
  --condition cohesive --run-id example-good \
  --output-root /private/tmp/cohesive-eval-runs \
  --patch relations/oracle/load-search-mapping/qualification/patches/cohesive/LSM-QUAL-GOOD-COH.patch
```

`run.sh` and `validate.sh` remain thin compatibility launchers. `--patch` is
repeatable and relative paths are resolved from the repository root. `--config`
selects a configuration file. `DOTNET_CLI` can select an SDK executable;
`COHESIVE_EVAL_DOTNET_CLI_HOME` selects its writable home. Paths are passed as
subprocess arguments, never shell command strings.

The runner exports only the pinned condition Git tree, checks its top-level
allowlist and leakage markers, and initializes fresh single-commit Git history.
It preserves the submitted workspace and binary-capable patch, audits again, and
scores a separate copy without Git metadata. The independently exported pinned
oracle is never placed in the participant workspace. Audits reject symlinks,
nested Git metadata and known evaluation-material indicators; these finite
checks do not constitute a general security sandbox for adversarial submissions.

## Evidence and classification

Each unused run ID creates its own directory with `workspace/`, `scoring/`,
`inputs/`, `agent/`, `evidence/` and `run.json`. It retains exact config/schema,
patch input hashes, pre/post file manifests, submitted diff, Git status, raw
build/test/scorer logs, visible-test TRX reports, oracle output when present, and
normalized gates/obligations. Existing run IDs are refused with exit 73; records
and files are never overwritten by a later invocation. Directory immutability
is otherwise a caller responsibility.

`config.v0.1.json` pins candidate baseline/oracle trees, task text, obligation
allocation, treatment check IDs, leakage rules and a 120-second per-command
infrastructure timeout. `run-record.schema.json` preserves the v1 score format;
runner version `0.2-python-candidate` identifies the port. This is not an agent
task budget or a frozen campaign manifest.

| Evidence | Classification |
|---|---|
| All contract, visible, hidden and treatment checks pass | valid / complete; exit 0 |
| C#/F#/VB compiler diagnostics on submission or adapter build; executed visible assertions fail; complete oracle report records failed checks | valid / incomplete; exit 0 |
| Restore failure, command launch/timeout failure, compiler-process failure without attributable compiler diagnostics, test host without usable TRX evidence | invalid / notScored; exit 2 |
| Missing/malformed oracle report, missing/duplicate/unexpected check or obligation IDs, inconsistent aggregation, wrong condition/schema, or unexpected/inconsistent exit code | invalid / notScored; exit 2 |

The pinned oracle catches submission exceptions within its checks and emits failed
check evidence; those remain valid incomplete outcomes. A missing report cannot
establish submission fault, so the runner does not charge it to the participant.
A scorer process exit 70 cannot become a valid result even if it leaves JSON behind.
Raw invalid reports are retained, while unestablished obligation results remain
notEvaluated. Recognized transient csc crashes retain one retry; the retry's own
diagnostics determine its classification. Setup errors before a usable run/config
exists exit nonzero and may not have a normalized record.

## Validate without a model

```sh
python3 -B -m unittest discover -s relations/runner -p 'test_*.py'
python3 -B relations/runner/validate.py
python3 -B relations/runner/validate_failures.py
```

The original `validation-cases.json` is unchanged: two untouched baselines, two
known-correct patches and one incompatible-contract patch must retain their exact
completion gates and obligation/treatment vectors. Validation also checks saved
evidence, workspace manifests and isolation. `validate_failures.py` delegates to
the real SDK while injecting restore/build/test-host/scorer failures and corrupt
reports. Each injected case must reach its intended failure and retain an invalid
record, and retrying a run ID must leave evidence unchanged. Both scripts accept
an optional unused output directory and otherwise print a retained temporary path.

For JSON Schema validation of their run records, install the test-only dependency
in a virtual environment and run:

```sh
python3 -m pip install -r relations/runner/requirements-test.txt
python3 relations/runner/validate_records.py /path/to/validation /path/to/failure-validation
```

Reference pins and supplied patches remain unchanged by this port. No hidden
results enter ordinary participant feedback, and no agent runs are authorized.
