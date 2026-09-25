# HYDRA Candidate Artifact Validation Runner Execution Scaffold Acceptance Gate Report v0.1.3

## Status

- overall_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_RUNNER_EXECUTION_SCAFFOLD_ACCEPTED`
- candidate_artifact_validation_runner_execution_scaffold_accepted: `True`
- content_execution_complete: `True`
- human_accepted: `True`
- scaffold_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_RUNNER_EXECUTION_SCAFFOLD_MATERIALIZED_READY_FOR_REVIEW`
- prior_acceptance_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_SCAFFOLD_ACCEPTED`
- source_scaffold_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_SCAFFOLD_MATERIALIZED_READY_FOR_REVIEW`
- prior_locator_classification: `CANDIDATE_SYMBOL_SPECIFIC_ARTIFACT_FOUND_WITHIN_BOUNDED_LOCATOR`

## Prior Evidence

- candidate_artifacts_written: `50`
- candidate_metadata_rows_read: `50`
- files_considered: `4866`
- roots_existing: `3`

## Counts

- pass_count: `21`
- fail_required_count: `0`
- critical_fail_count: `0`
- warning_count: `0`
- guardrail_violation_count: `0`
- execution_plan_rows_read: `18`
- runner_contract_rows_read: `13`
- validation_execution_contract_rows_read: `12`
- diagnostic_output_contract_rows_read: `10`
- audit_contract_rows_read: `8`
- guardrail_rows_read: `52`

## Guardrails

No candidate artifact file content read, candidate header read, candidate row read, market source read, candidate validation execution, symbol mapping, normalization transform, join, production rows, mutation, cap widening, simulation, or execution was performed.

## Next Valid Action

build/run candidate artifact validation runner v0.1.3 only after this scaffold is accepted; validation remains bounded diagnostics-only
