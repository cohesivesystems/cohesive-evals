#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
oracle_root="$(cd "$script_dir/.." && pwd)"
repository_root="$(cd "$oracle_root/../../.." && pwd)"
case_root="$repository_root/relations/cases/load-search-mapping"
oracle_project="$oracle_root/src/LoadSearch.Oracle/LoadSearch.Oracle.csproj"
cases_file="$script_dir/cases.json"
output_file="${1:-$script_dir/observed.json}"
dotnet_cli="${DOTNET_CLI:-/usr/local/share/dotnet/dotnet}"
qualification_root="$(mktemp -d /private/tmp/load-search-oracle-qualification.XXXXXX)"
results_file="$qualification_root/results.jsonl"

cleanup() {
  rm -rf "$qualification_root"
}
trap cleanup EXIT

export DOTNET_CLI_HOME="${COH58_DOTNET_CLI_HOME:-/tmp/coh58-dotnet-home}"
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1

run_dotnet() {
  "$dotnet_cli" "$@" -m:1 -p:UseSharedCompilation=false -nodeReuse:false
}

while IFS= read -r qualification_case; do
  id="$(jq -r '.id' <<<"$qualification_case")"
  condition="$(jq -r '.condition' <<<"$qualification_case")"
  case_directory="$qualification_root/$id"
  workspace="$case_directory/workspace"
  mkdir -p "$case_directory"
  cp -R "$case_root/conditions/$condition" "$workspace"
  find "$workspace" -type d \( -name bin -o -name obj \) -prune -exec rm -rf {} +
  while IFS= read -r relative_patch; do
    git -C "$workspace" apply "$script_dir/$relative_patch"
  done < <(jq -r '.patches[]' <<<"$qualification_case")

  restore_log="$case_directory/restore.log"
  build_log="$case_directory/build.log"
  visible_log="$case_directory/visible-tests.log"
  oracle_log="$case_directory/oracle.log"
  oracle_report="$case_directory/oracle.json"

  if ! run_dotnet restore "$workspace/LoadSearch.slnx" \
    --configfile "$workspace/NuGet.config" >"$restore_log" 2>&1; then
    cat "$restore_log" >&2
    printf '%s: dependency restore failed; qualification aborted\n' "$id" >&2
    exit 2
  fi

  if run_dotnet build "$workspace/LoadSearch.slnx" --no-restore >"$build_log" 2>&1; then
    find "$oracle_root/src/LoadSearch.Oracle" -type d \( -name bin -o -name obj \) -prune -exec rm -rf {} +
    if ! run_dotnet restore "$oracle_project" \
      --configfile "$workspace/NuGet.config" \
      -p:SubmissionRoot="$workspace" >"$oracle_log" 2>&1; then
      cat "$oracle_log" >&2
      printf '%s: oracle dependency restore failed; qualification aborted\n' "$id" >&2
      exit 2
    fi

    if run_dotnet build "$oracle_project" --no-restore \
      -p:SubmissionRoot="$workspace" >>"$oracle_log" 2>&1; then
      contract_build="passed"
      if run_dotnet test "$workspace/LoadSearch.slnx" --no-build --no-restore >"$visible_log" 2>&1; then
        visible_tests="passed"
      else
        visible_tests="failed"
      fi

      oracle_dll="$oracle_root/src/LoadSearch.Oracle/bin/Debug/net10.0/LoadSearch.Oracle.dll"
      if "$dotnet_cli" "$oracle_dll" \
        --condition "$condition" \
        --submission-root "$workspace" \
        --output "$oracle_report" >>"$oracle_log" 2>&1; then
        oracle_exit="passed"
      else
        oracle_exit="failed"
      fi
    else
      contract_build="failed"
      visible_tests="notEvaluated"
      oracle_exit="notEvaluated"
    fi
  else
    contract_build="failed"
    visible_tests="notEvaluated"
    oracle_exit="notEvaluated"
  fi

  if [[ -f "$oracle_report" ]]; then
    oracle_json="$(jq -c '.' "$oracle_report")"
  else
    oracle_json="null"
  fi

  artifacts="[]"
  while IFS= read -r artifact; do
    artifact_sha="$(shasum -a 256 "$script_dir/$artifact" | awk '{print $1}')"
    artifacts="$(jq -c \
      --arg path "$artifact" \
      --arg sha256 "$artifact_sha" \
      '. + [{path: $path, sha256: $sha256}]' <<<"$artifacts")"
  done < <(jq -r '.patches[]' <<<"$qualification_case")

  jq -cn \
    --arg id "$id" \
    --arg condition "$condition" \
    --arg contractBuild "$contract_build" \
    --arg visibleTests "$visible_tests" \
    --arg oracleExit "$oracle_exit" \
    --argjson artifacts "$artifacts" \
    --argjson oracle "$oracle_json" '
      {
        id: $id,
        condition: $condition,
        artifacts: $artifacts,
        observed: {
          contractBuild: $contractBuild,
          visibleTests: $visibleTests,
          oracleExit: $oracleExit,
          failedBehavioralChecks: (if $oracle == null then null else
            [$oracle.behavioralChecks[] | select(.status == "failed") | .id] end),
          failedObligations: (if $oracle == null then null else
            [$oracle.obligations[] | select(.status == "failed") | .id] end),
          failedTreatmentIntegrityChecks: (if $oracle == null then null else
            [$oracle.treatmentIntegrityChecks[] | select(.status == "failed") | .id] end),
          treatmentIntegrity: ($oracle.treatmentIntegrity // null),
          oracleOutcome: ($oracle.outcome // null)
        }
      }' >>"$results_file"
  printf '%s: build=%s visible=%s oracle=%s\n' "$id" "$contract_build" "$visible_tests" "$oracle_exit"
done < <(jq -c '.cases[]' "$cases_file")

mkdir -p "$(dirname "$output_file")"
jq -s \
  --arg revision "$(jq -r '.baselineRevision' "$cases_file")" '
    {
      schemaVersion: "cohesive.relations.load-search.qualification-observed/v1",
      baselineRevision: $revision,
      cases: .
    }' "$results_file" >"$output_file"

expected="$qualification_root/expected.json"
actual="$qualification_root/actual.json"
jq '{baselineRevision, cases: [.cases[] | {id, expected}]}' "$cases_file" >"$expected"
jq '{baselineRevision, cases: [.cases[] | {id, expected: .observed}]}' "$output_file" >"$actual"

if ! diff -u "$expected" "$actual"; then
  printf 'Qualification results did not match the declared expectations.\n' >&2
  exit 1
fi

printf 'Wrote %s; all qualification vectors matched.\n' "$output_file"
