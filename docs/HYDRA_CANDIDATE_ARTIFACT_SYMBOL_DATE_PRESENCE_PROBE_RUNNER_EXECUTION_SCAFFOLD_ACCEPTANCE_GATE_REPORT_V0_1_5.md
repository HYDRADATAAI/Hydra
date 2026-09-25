# HYDRA Candidate Artifact Symbol/Date Presence Probe Runner Execution Scaffold Acceptance Gate Report v0.1.5

## Status

- overall_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_SYMBOL_DATE_PRESENCE_PROBE_RUNNER_EXECUTION_SCAFFOLD_ACCEPTED`
- candidate_artifact_symbol_date_presence_probe_runner_execution_scaffold_accepted: `True`
- content_execution_complete: `True`
- human_accepted: `True`
- scaffold_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_SYMBOL_DATE_PRESENCE_PROBE_RUNNER_EXECUTION_SCAFFOLD_MATERIALIZED_READY_FOR_REVIEW`
- prior_acceptance_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_SYMBOL_DATE_PRESENCE_PROBE_SCAFFOLD_ACCEPTED`
- source_scaffold_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_SYMBOL_DATE_PRESENCE_PROBE_SCAFFOLD_MATERIALIZED_READY_FOR_REVIEW`
- prior_content_probe_classification: `CONTROLLED_CANDIDATE_ARTIFACT_CONTENT_PROBE_COMPLETE_SAMPLE_ROWS_OBSERVED`

## Prior Evidence

- schema_hint: `symbol|timestamp|open|high|low|close|volume|source|timeframe|continuous|adjustment`
- value_hint: `MNQ=10`
- sample_rows_observed: `10`
- selected_candidate_count: `1`

## Counts

- pass_count: `22`
- fail_required_count: `0`
- critical_fail_count: `0`
- warning_count: `0`
- guardrail_violation_count: `0`
- execution_plan_rows_read: `18`
- runner_contract_rows_read: `13`
- symbol_date_presence_execution_contract_rows_read: `12`
- evidence_output_contract_rows_read: `10`
- audit_contract_rows_read: `8`
- guardrail_rows_read: `52`

## Guardrails

No symbol/date presence probe, file read, candidate row read, symbol mapping, normalization transform, join, production rows, mutation, cap widening, derived metric calculation, simulation, or execution was performed.

## Next Valid Action

build/run candidate artifact symbol/date presence probe runner v0.1.5 only after this scaffold is accepted; probe remains bounded diagnostics-only
