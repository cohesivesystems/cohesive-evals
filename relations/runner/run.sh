#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(git -C "$script_dir" rev-parse --show-toplevel)"
config_file="$script_dir/config.v0.1.json"
condition=""
run_id=""
output_root=""
patches=()
patch_count=0

usage() {
  printf '%s\n' \
    'Usage: run.sh --condition conventional|cohesive --run-id ID --output-root DIR [--patch FILE ...]' \
    '' \
    'Creates one immutable dry-run record. A valid incomplete submission still exits 0;' \
    'runner or dependency infrastructure failure exits 2.'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --condition)
      condition="${2:-}"
      shift 2
      ;;
    --run-id)
      run_id="${2:-}"
      shift 2
      ;;
    --output-root)
      output_root="${2:-}"
      shift 2
      ;;
    --config)
      config_file="${2:-}"
      shift 2
      ;;
    --patch)
      patches+=("${2:-}")
      patch_count=$((patch_count + 1))
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown or incomplete argument: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

for dependency in git jq rg shasum tar; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "$dependency" >&2
    exit 69
  fi
done

dotnet_cli="${DOTNET_CLI:-dotnet}"
if ! command -v "$dotnet_cli" >/dev/null 2>&1 && [[ ! -x "$dotnet_cli" ]]; then
  printf 'Required .NET CLI not found: %s\n' "$dotnet_cli" >&2
  exit 69
fi

if [[ ! -f "$config_file" ]]; then
  printf 'Runner config not found: %s\n' "$config_file" >&2
  exit 66
fi
config_file="$(cd "$(dirname "$config_file")" && pwd)/$(basename "$config_file")"

if [[ "$condition" != "conventional" && "$condition" != "cohesive" ]]; then
  printf 'Provide --condition conventional|cohesive.\n' >&2
  exit 64
fi
if [[ ! "$run_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  printf 'Provide a filesystem-safe --run-id.\n' >&2
  exit 64
fi
if [[ -z "$output_root" ]]; then
  printf 'Provide --output-root DIR.\n' >&2
  exit 64
fi

mkdir -p "$output_root"
output_root="$(cd "$output_root" && pwd)"
run_dir="$output_root/$run_id"
if [[ -e "$run_dir" ]]; then
  printf 'Run directory already exists and will not be overwritten: %s\n' "$run_dir" >&2
  exit 73
fi

mkdir -p \
  "$run_dir/workspace" \
  "$run_dir/scoring/submission" \
  "$run_dir/scoring/oracle" \
  "$run_dir/evidence/logs" \
  "$run_dir/evidence/manifests" \
  "$run_dir/inputs/patches" \
  "$run_dir/agent"

started_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
started_epoch="$(date +%s)"
ended_at=""
elapsed_seconds=0
validity="valid"
invalid_reason=""
outcome="incomplete"
dependency_restore="notEvaluated"
application_build="notEvaluated"
visible_tests="notEvaluated"
oracle_adapter_build="notEvaluated"
contract_build="notEvaluated"
oracle_execution="notEvaluated"
oracle_exit_code=""
hidden_checks="notEvaluated"
treatment_integrity="notEvaluated"
pre_audit="notEvaluated"
post_audit="notEvaluated"
workspace_audit="notEvaluated"
baseline_workspace_commit=""
changed_file_count=0
patch_line_count=0
oracle_report_relative=""

runner_version="$(jq -r '.runnerVersion' "$config_file")"
protocol_version="$(jq -r '.protocolVersion' "$config_file")"
case_id="$(jq -r '.caseId' "$config_file")"
task_id="$(jq -r '.taskId' "$config_file")"
task_text="$(jq -r '.task' "$config_file")"
baseline_revision="$(jq -r '.baselineRevision' "$config_file")"
condition_path="$(jq -r --arg condition "$condition" '.conditions[$condition].path' "$config_file")"
condition_tree="$(jq -r --arg condition "$condition" '.conditions[$condition].tree' "$config_file")"
oracle_revision="$(jq -r '.oracle.revision' "$config_file")"
oracle_path="$(jq -r '.oracle.path' "$config_file")"
oracle_tree="$(jq -r '.oracle.tree' "$config_file")"
config_sha256="$(shasum -a 256 "$config_file" | awk '{print $1}')"
runner_source_revision="$(git -C "$repository_root" rev-parse HEAD)"
if [[ -n "$(git -C "$repository_root" status --porcelain -- relations/runner)" ]]; then
  runner_source_dirty=true
else
  runner_source_dirty=false
fi
dotnet_version="$($dotnet_cli --version)"
host_os="$(uname -s)"
host_arch="$(uname -m)"

workspace="$run_dir/workspace"
submission="$run_dir/scoring/submission"
oracle_workspace="$run_dir/scoring/oracle"
logs="$run_dir/evidence/logs"
manifests="$run_dir/evidence/manifests"
patch_inputs_file="$run_dir/inputs/patches.json"
obligation_results_file="$run_dir/evidence/obligations.json"
oracle_report="$run_dir/evidence/oracle-report.json"

printf '[]\n' >"$patch_inputs_file"
jq '[.obligationIds[] | {id: ., status: "notEvaluated", checks: []}]' \
  "$config_file" >"$obligation_results_file"
printf '{"schemaVersion":"cohesive.relations.workspace-manifest/v1","files":[]}\n' \
  >"$manifests/pre.json"
printf '{"schemaVersion":"cohesive.relations.workspace-manifest/v1","files":[]}\n' \
  >"$manifests/post.json"
for evidence_file in \
  "$logs/application-restore.log" \
  "$logs/application-build.log" \
  "$logs/visible-tests.log" \
  "$logs/oracle-restore.log" \
  "$logs/oracle-build.log" \
  "$logs/oracle-execution.log" \
  "$logs/patch-application.log" \
  "$run_dir/evidence/git-status.txt" \
  "$run_dir/evidence/final.patch" \
  "$run_dir/agent/stdout.log" \
  "$run_dir/agent/stderr.log"; do
  : >"$evidence_file"
done

write_manifest() {
  local root="$1"
  local output="$2"
  local lines="$output.lines"
  : >"$lines"
  while IFS= read -r file; do
    local relative="${file#"$root"/}"
    local size
    local sha256
    size="$(wc -c <"$file" | tr -d ' ')"
    sha256="$(shasum -a 256 "$file" | awk '{print $1}')"
    jq -cn \
      --arg path "$relative" \
      --arg sha256 "$sha256" \
      --argjson size "$size" \
      '{path: $path, size: $size, sha256: $sha256}' >>"$lines"
  done < <(find "$root" -type f ! -path "$root/.git/*" -print | LC_ALL=C sort)
  jq -s '{schemaVersion: "cohesive.relations.workspace-manifest/v1", files: .}' \
    "$lines" >"$output"
  rm -f "$lines"
}

audit_workspace() {
  local root="$1"
  local require_exact_top_level="$2"
  local log="$3"
  local failed=0
  local found
  local expected="$log.expected"
  local actual="$log.actual"

  : >"$log"
  printf 'Workspace audit: %s\n' "$root" >>"$log"

  found="$(find "$root" -path "$root/.git" -prune -o -type l -print)"
  if [[ -n "$found" ]]; then
    printf 'Symlinks are not allowed:\n%s\n' "$found" >>"$log"
    failed=1
  fi

  while IFS= read -r forbidden_name; do
    found="$(find "$root" -path "$root/.git" -prune -o -name "$forbidden_name" -print)"
    if [[ -n "$found" ]]; then
      printf 'Forbidden path name %s:\n%s\n' "$forbidden_name" "$found" >>"$log"
      failed=1
    fi
  done < <(jq -r '.forbiddenPathNames[]' "$config_file")

  while IFS= read -r forbidden_text; do
    if rg --hidden -I -n -F -g '!.git/**' -- "$forbidden_text" "$root" >>"$log" 2>&1; then
      printf 'Forbidden text matched: %s\n' "$forbidden_text" >>"$log"
      failed=1
    fi
  done < <(jq -r '.forbiddenText[]' "$config_file")

  if [[ "$require_exact_top_level" == "true" ]]; then
    jq -r --arg condition "$condition" '.conditions[$condition].allowedTopLevel[]' \
      "$config_file" | LC_ALL=C sort >"$expected"
    find "$root" -mindepth 1 -maxdepth 1 ! -name .git -exec basename {} \; \
      | LC_ALL=C sort >"$actual"
    if ! diff -u "$expected" "$actual" >>"$log" 2>&1; then
      printf 'Top-level allowlist mismatch.\n' >>"$log"
      failed=1
    fi
    rm -f "$expected" "$actual"
  fi

  if [[ "$failed" -eq 0 ]]; then
    printf 'Audit passed.\n' >>"$log"
    return 0
  fi
  return 1
}

write_record() {
  ended_at="${ended_at:-$(date -u +'%Y-%m-%dT%H:%M:%SZ')}"
  elapsed_seconds="$(($(date +%s) - started_epoch))"
  jq -n \
    --arg runId "$run_id" \
    --arg condition "$condition" \
    --arg validity "$validity" \
    --arg invalidReason "$invalid_reason" \
    --arg outcome "$outcome" \
    --arg runnerVersion "$runner_version" \
    --arg runnerSourceRevision "$runner_source_revision" \
    --argjson runnerSourceDirty "$runner_source_dirty" \
    --arg configSha256 "$config_sha256" \
    --arg protocolVersion "$protocol_version" \
    --arg caseId "$case_id" \
    --arg taskId "$task_id" \
    --arg task "$task_text" \
    --arg baselineRevision "$baseline_revision" \
    --arg conditionTree "$condition_tree" \
    --arg oracleRevision "$oracle_revision" \
    --arg oracleTree "$oracle_tree" \
    --arg dotnetVersion "$dotnet_version" \
    --arg hostOs "$host_os" \
    --arg hostArch "$host_arch" \
    --arg startedAt "$started_at" \
    --arg endedAt "$ended_at" \
    --argjson elapsedSeconds "$elapsed_seconds" \
    --arg baselineWorkspaceCommit "$baseline_workspace_commit" \
    --argjson changedFileCount "$changed_file_count" \
    --argjson patchLineCount "$patch_line_count" \
    --arg preAudit "$pre_audit" \
    --arg postAudit "$post_audit" \
    --arg workspaceAudit "$workspace_audit" \
    --arg dependencyRestore "$dependency_restore" \
    --arg applicationBuild "$application_build" \
    --arg visibleTests "$visible_tests" \
    --arg oracleAdapterBuild "$oracle_adapter_build" \
    --arg contractBuild "$contract_build" \
    --arg oracleExecution "$oracle_execution" \
    --arg oracleExitCode "$oracle_exit_code" \
    --arg hiddenChecks "$hidden_checks" \
    --arg treatmentIntegrity "$treatment_integrity" \
    --arg oracleReport "$oracle_report_relative" \
    --slurpfile patchInputs "$patch_inputs_file" \
    --slurpfile obligations "$obligation_results_file" '
      {
        schemaVersion: "cohesive.relations.run-record/v1",
        runId: $runId,
        phase: "dryRun",
        condition: $condition,
        validity: $validity,
        invalidReason: (if $invalidReason == "" then null else $invalidReason end),
        outcome: $outcome,
        configuration: {
          runnerVersion: $runnerVersion,
          runnerSourceRevision: $runnerSourceRevision,
          runnerSourceDirty: $runnerSourceDirty,
          configSha256: $configSha256,
          protocolVersion: $protocolVersion,
          caseId: $caseId,
          taskId: $taskId,
          task: $task,
          baselineRevision: $baselineRevision,
          conditionTree: $conditionTree,
          oracleRevision: $oracleRevision,
          oracleTree: $oracleTree,
          dotnetSdk: $dotnetVersion,
          host: {os: $hostOs, architecture: $hostArch}
        },
        timing: {
          startedAt: $startedAt,
          endedAt: $endedAt,
          elapsedSeconds: $elapsedSeconds
        },
        workspace: {
          baselineCommit: (if $baselineWorkspaceCommit == "" then null else $baselineWorkspaceCommit end),
          changedFileCount: $changedFileCount,
          preManifest: "evidence/manifests/pre.json",
          postManifest: "evidence/manifests/post.json"
        },
        submission: {
          appliedInputs: $patchInputs[0],
          finalPatch: "evidence/final.patch",
          patchLineCount: $patchLineCount
        },
        agent: {
          mode: "dryRunPatchReplay",
          invoked: false,
          stdout: "agent/stdout.log",
          stderr: "agent/stderr.log"
        },
        gates: {
          preWorkspaceAudit: $preAudit,
          postWorkspaceAudit: $postAudit,
          workspaceAudit: $workspaceAudit,
          dependencyRestore: $dependencyRestore,
          applicationBuild: $applicationBuild,
          visibleTests: $visibleTests,
          oracleAdapterBuild: $oracleAdapterBuild,
          contractBuild: $contractBuild,
          oracleExecution: $oracleExecution,
          oracleExitCode: (if $oracleExitCode == "" then null else ($oracleExitCode | tonumber) end),
          hiddenChecks: $hiddenChecks,
          treatmentIntegrity: $treatmentIntegrity
        },
        obligations: $obligations[0],
        evidence: {
          applicationRestoreLog: "evidence/logs/application-restore.log",
          applicationBuildLog: "evidence/logs/application-build.log",
          visibleTestsLog: "evidence/logs/visible-tests.log",
          oracleRestoreLog: "evidence/logs/oracle-restore.log",
          oracleBuildLog: "evidence/logs/oracle-build.log",
          oracleExecutionLog: "evidence/logs/oracle-execution.log",
          oracleReport: (if $oracleReport == "" then null else $oracleReport end),
          gitStatus: "evidence/git-status.txt"
        }
      }' >"$run_dir/run.json"
}

infrastructure_fail() {
  validity="invalid"
  invalid_reason="$1"
  outcome="notScored"
  ended_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  write_record
  printf 'Runner infrastructure failure: %s\nRecord: %s\n' "$invalid_reason" "$run_dir/run.json" >&2
  exit 2
}

finish_valid() {
  validity="valid"
  invalid_reason=""
  ended_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  write_record
  printf 'Run %s: validity=%s outcome=%s\nRecord: %s\n' \
    "$run_id" "$validity" "$outcome" "$run_dir/run.json"
  exit 0
}

run_dotnet() {
  "$dotnet_cli" "$@" -m:1 -p:UseSharedCompilation=false -nodeReuse:false
}

actual_condition_tree="$(git -C "$repository_root" rev-parse "$baseline_revision:$condition_path" 2>/dev/null || true)"
if [[ "$actual_condition_tree" != "$condition_tree" ]]; then
  infrastructure_fail "Pinned condition tree did not match config."
fi
actual_oracle_tree="$(git -C "$repository_root" rev-parse "$oracle_revision:$oracle_path" 2>/dev/null || true)"
if [[ "$actual_oracle_tree" != "$oracle_tree" ]]; then
  infrastructure_fail "Pinned oracle tree did not match config."
fi

if ! (git -C "$repository_root" archive "$baseline_revision:$condition_path" | tar -x -C "$workspace"); then
  infrastructure_fail "Could not export the pinned condition workspace."
fi
write_manifest "$workspace" "$manifests/pre.json"
if audit_workspace "$workspace" true "$logs/pre-workspace-audit.log"; then
  pre_audit="passed"
else
  pre_audit="failed"
  infrastructure_fail "Pre-run workspace audit failed."
fi

git -C "$workspace" init -q
git -C "$workspace" config user.name "Cohesive Evaluation Runner"
git -C "$workspace" config user.email "runner@invalid.local"
git -C "$workspace" add -A
source_date="$(git -C "$repository_root" show -s --format=%aI "$baseline_revision")"
GIT_AUTHOR_DATE="$source_date" GIT_COMMITTER_DATE="$source_date" \
  git -C "$workspace" commit -q -m "Evaluation baseline"
baseline_workspace_commit="$(git -C "$workspace" rev-parse HEAD)"

patch_lines="$run_dir/inputs/patches.jsonl"
: >"$patch_lines"
patch_index=0
if [[ "$patch_count" -gt 0 ]]; then
  for patch in "${patches[@]}"; do
    patch_index=$((patch_index + 1))
    if [[ "$patch" = /* ]]; then
      patch_source="$patch"
    else
      patch_source="$repository_root/$patch"
    fi
    if [[ ! -f "$patch_source" ]]; then
      infrastructure_fail "Submission patch not found: $patch"
    fi
    patch_name="$(printf '%02d-%s' "$patch_index" "$(basename "$patch_source")")"
    patch_copy="$run_dir/inputs/patches/$patch_name"
    cp "$patch_source" "$patch_copy"
    patch_sha256="$(shasum -a 256 "$patch_copy" | awk '{print $1}')"
    jq -cn \
      --arg path "inputs/patches/$patch_name" \
      --arg sha256 "$patch_sha256" \
      '{path: $path, sha256: $sha256}' >>"$patch_lines"
    if ! git -C "$workspace" apply "$patch_copy" >>"$logs/patch-application.log" 2>&1; then
      infrastructure_fail "Submission patch did not apply: $patch"
    fi
  done
fi
jq -s '.' "$patch_lines" >"$patch_inputs_file"
rm -f "$patch_lines"

printf 'Dry-run patch replay; no coding agent was invoked.\nApplied patch count: %s\n' \
  "$patch_count" >"$run_dir/agent/stdout.log"
: >"$run_dir/agent/stderr.log"

write_manifest "$workspace" "$manifests/post.json"
if audit_workspace "$workspace" false "$logs/post-workspace-audit.log"; then
  post_audit="passed"
  workspace_audit="passed"
else
  post_audit="failed"
  workspace_audit="failed"
  infrastructure_fail "Post-run workspace audit failed."
fi

git -C "$workspace" status --porcelain=v1 >"$run_dir/evidence/git-status.txt"
git -C "$workspace" add -N -- .
git -C "$workspace" diff --binary --no-ext-diff >"$run_dir/evidence/final.patch"
changed_file_count="$(git -C "$workspace" status --porcelain=v1 | wc -l | tr -d ' ')"
patch_line_count="$(wc -l <"$run_dir/evidence/final.patch" | tr -d ' ')"

if ! ((cd "$workspace" && tar --exclude=.git -cf - .) | (cd "$submission" && tar -xf -)); then
  infrastructure_fail "Could not preserve the submission in the scoring workspace."
fi
if ! (git -C "$repository_root" archive "$oracle_revision:$oracle_path" | tar -x -C "$oracle_workspace"); then
  infrastructure_fail "Could not export the pinned oracle."
fi

export DOTNET_CLI_HOME="${COHESIVE_EVAL_DOTNET_CLI_HOME:-/tmp/cohesive-evals-dotnet-home}"
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1
mkdir -p "$DOTNET_CLI_HOME"

if run_dotnet restore "$submission/LoadSearch.slnx" \
  --configfile "$submission/NuGet.config" >"$logs/application-restore.log" 2>&1; then
  dependency_restore="passed"
else
  dependency_restore="failed"
  infrastructure_fail "Application dependency restore failed."
fi

if run_dotnet build "$submission/LoadSearch.slnx" --no-restore \
  >"$logs/application-build.log" 2>&1; then
  application_build="passed"
else
  if rg -q 'MSB6006: "csc" exited with code (134|139)' "$logs/application-build.log"; then
    printf '\nTransient compiler-process failure detected; retrying scoring build once.\n' \
      >>"$logs/application-build.log"
    if run_dotnet build "$submission/LoadSearch.slnx" --no-restore \
      >>"$logs/application-build.log" 2>&1; then
      application_build="passed"
    else
      infrastructure_fail "Application compiler process failed twice during scoring."
    fi
  else
    application_build="failed"
    contract_build="failed"
    outcome="incomplete"
    finish_valid
  fi
fi

if run_dotnet test "$submission/LoadSearch.slnx" --no-build --no-restore \
  >"$logs/visible-tests.log" 2>&1; then
  visible_tests="passed"
else
  visible_tests="failed"
fi

oracle_project="$oracle_workspace/LoadSearch.Oracle.csproj"
if run_dotnet restore "$oracle_project" \
  --configfile "$submission/NuGet.config" \
  -p:SubmissionRoot="$submission" >"$logs/oracle-restore.log" 2>&1; then
  :
else
  infrastructure_fail "Oracle dependency restore failed."
fi

if run_dotnet build "$oracle_project" --no-restore \
  -p:SubmissionRoot="$submission" >"$logs/oracle-build.log" 2>&1; then
  oracle_adapter_build="passed"
  contract_build="passed"
else
  if rg -q 'MSB6006: "csc" exited with code (134|139)' "$logs/oracle-build.log"; then
    printf '\nTransient compiler-process failure detected; retrying oracle build once.\n' \
      >>"$logs/oracle-build.log"
    if run_dotnet build "$oracle_project" --no-restore \
      -p:SubmissionRoot="$submission" >>"$logs/oracle-build.log" 2>&1; then
      oracle_adapter_build="passed"
      contract_build="passed"
    else
      infrastructure_fail "Oracle compiler process failed twice during scoring."
    fi
  else
    oracle_adapter_build="failed"
    contract_build="failed"
    outcome="incomplete"
    finish_valid
  fi
fi

oracle_dll="$oracle_workspace/bin/Debug/net10.0/LoadSearch.Oracle.dll"
if "$dotnet_cli" "$oracle_dll" \
  --condition "$condition" \
  --submission-root "$submission" \
  --output "$oracle_report" >"$logs/oracle-execution.log" 2>&1; then
  oracle_exit_code=0
else
  oracle_exit_code=$?
fi

if [[ -f "$oracle_report" ]] && jq empty "$oracle_report" >/dev/null 2>&1; then
  oracle_execution="passed"
  oracle_report_relative="evidence/oracle-report.json"
  jq '[.obligations[] | {id, status, checks}]' "$oracle_report" >"$obligation_results_file"
  hidden_checks="$(jq -r 'if all(.obligations[]; .status == "passed") then "passed" else "failed" end' "$oracle_report")"
  treatment_integrity="$(jq -r '.treatmentIntegrity' "$oracle_report")"
else
  oracle_execution="failed"
  hidden_checks="notEvaluated"
  treatment_integrity="notEvaluated"
fi

if [[ "$contract_build" == "passed" \
  && "$visible_tests" == "passed" \
  && "$hidden_checks" == "passed" \
  && "$treatment_integrity" == "passed" ]]; then
  outcome="complete"
else
  outcome="incomplete"
fi

finish_valid
