#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cases_file="$script_dir/validation-cases.json"
runner="$script_dir/run.sh"
output_root="${1:-$(mktemp -d /private/tmp/cohesive-runner-validation.XXXXXX)}"
mkdir -p "$output_root"
output_root="$(cd "$output_root" && pwd)"
comparison_root="$(mktemp -d /private/tmp/cohesive-runner-comparison.XXXXXX)"

case_count=0
while IFS= read -r validation_case; do
  id="$(jq -r '.id' <<<"$validation_case")"
  condition="$(jq -r '.condition' <<<"$validation_case")"
  command=(
    "$runner"
    --condition "$condition"
    --run-id "$id"
    --output-root "$output_root"
  )
  while IFS= read -r patch; do
    command+=(--patch "$patch")
  done < <(jq -r '.patches[]' <<<"$validation_case")

  "${command[@]}"
  record="$output_root/$id/run.json"
  actual="$comparison_root/$id.actual.json"
  expected="$comparison_root/$id.expected.json"
  jq '{
    validity,
    outcome,
    contractBuild: .gates.contractBuild,
    visibleTests: .gates.visibleTests,
    hiddenChecks: .gates.hiddenChecks,
    treatmentIntegrity: .gates.treatmentIntegrity,
    failedObligations: [.obligations[] | select(.status == "failed") | .id],
    notEvaluatedObligations: [.obligations[] | select(.status == "notEvaluated") | .id]
  }' "$record" >"$actual"
  jq '.expected' <<<"$validation_case" >"$expected"
  if ! diff -u "$expected" "$actual"; then
    printf 'Runner validation mismatch: %s\n' "$id" >&2
    exit 1
  fi
  case_count=$((case_count + 1))
done < <(jq -c '.cases[]' "$cases_file")

printf 'Validated %s runner cases.\nEvidence: %s\n' "$case_count" "$output_root"
