# HYDRA Candidate Artifact Symbol/Date Presence Probe Runner Result Acceptance Gate Report v0.1.5

## Status

- overall_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_SYMBOL_DATE_PRESENCE_PROBE_RUNNER_RESULT_ACCEPTED`
- candidate_artifact_symbol_date_presence_probe_runner_result_accepted: `True`
- content_execution_complete: `True`
- human_accepted: `True`
- runner_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_SYMBOL_DATE_PRESENCE_PROBE_RUNNER_COMPLETE`
- probe_complete: `True`
- diagnostics_only: `True`

## Classification

- overall_presence_classification: `CANDIDATE_ARTIFACT_SYMBOL_DATE_PRESENCE_CONFIRMED_WITHIN_BOUNDED_PROBE`
- recommended_next_resolution_path: `accept_checkpoint_then_prepare_candidate_artifact_join_readiness_scaffold_or_source_selection_checkpoint`

## Presence Evidence

- target_symbol: `MNQ`
- target_date: `2024-12-12`
- eligible_candidate_count: `1`
- selected_candidate_count: `1`
- rows_seen: `82702`
- bytes_read: `10477980`
- symbol_count: `82702`
- date_count: `46`
- both_match_count: `46`
- read_error_count: `0`

## Artifact Rows

- presence_summary_rows_read: `1`
- value_evidence_rows_read: `25`
- cap_usage_rows_read: `5`
- classification_rows_read: `2`
- runner_guardrail_rows_read: `29`
- runner_checks_rows_read: `16`

## Checks

- pass_count: `30`
- fail_required_count: `0`
- critical_fail_count: `0`
- warning_count: `0`

## Guardrails

No rerun, file read, symbol mapping, join, production rows, mutation, cap widening, derived metrics, simulation, or execution was performed by this acceptance gate.

## Next Valid Action

checkpoint accepted symbol/date presence result; then prepare candidate artifact join-readiness scaffold or source-selection checkpoint
