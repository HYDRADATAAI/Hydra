# HYDRA Candidate Artifact Validation Runner Result Acceptance Gate Report v0.1.3

## Status

- overall_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_RUNNER_RESULT_ACCEPTED`
- candidate_artifact_validation_runner_result_accepted: `True`
- content_execution_complete: `True`
- human_accepted: `True`
- runner_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_RUNNER_COMPLETE`
- validation_complete: `True`
- diagnostics_only: `True`

## Classification

- overall_validation_classification: `CANDIDATE_ARTIFACT_HEADER_VALIDATED_WITHIN_BOUNDED_PROBE`
- recommended_next_resolution_path: `accept_checkpoint_then_prepare_controlled_candidate_artifact_content_probe_scaffold`

## Validation Evidence

- candidate_metadata_rows_available: `50`
- selected_candidate_count: `5`
- identity_validated_count: `3`
- header_validated_count: `1`
- missing_paths: `0`
- header_probe_attempts: `5`
- total_header_bytes_read: `370`
- total_header_lines_read: `5`

## Artifact Rows

- candidate_identity_rows_read: `5`
- header_probe_summary_rows_read: `5`
- cap_usage_rows_read: `5`
- classification_rows_read: `2`
- runner_guardrail_rows_read: `28`
- runner_checks_rows_read: `13`

## Checks

- pass_count: `24`
- fail_required_count: `0`
- critical_fail_count: `0`
- warning_count: `0`

## Guardrails

No rerun, candidate data row read, market row read, symbol mapping, join, production rows, mutation, cap widening, simulation, or execution was performed by this acceptance gate.

## Next Valid Action

checkpoint accepted candidate artifact validation result; then prepare controlled candidate artifact content probe scaffold
