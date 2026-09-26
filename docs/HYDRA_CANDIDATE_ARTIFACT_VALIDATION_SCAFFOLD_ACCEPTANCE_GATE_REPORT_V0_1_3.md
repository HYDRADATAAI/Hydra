# HYDRA Candidate Artifact Validation Scaffold Acceptance Gate Report v0.1.3

## Status

- overall_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_SCAFFOLD_ACCEPTED`
- candidate_artifact_validation_scaffold_accepted: `True`
- content_execution_complete: `True`
- human_accepted: `True`
- scaffold_status: `PLANNER_MARKET_JOIN_CANDIDATE_ARTIFACT_VALIDATION_SCAFFOLD_MATERIALIZED_READY_FOR_REVIEW`
- prior_checkpoint_status: `PLANNER_MARKET_JOIN_SYMBOL_SPECIFIC_ARTIFACT_LOCATOR_RUNNER_RESULT_CHECK_OFF_READY`
- prior_locator_classification: `CANDIDATE_SYMBOL_SPECIFIC_ARTIFACT_FOUND_WITHIN_BOUNDED_LOCATOR`

## Prior Evidence

- candidate_artifacts_written: `50`
- candidate_metadata_rows_read: `50`
- files_considered: `4866`
- roots_existing: `3`
- candidate_summary: `1:HYDRA_mnq_30min_continuous_unadjusted_ohlcv_v0_1.csv:score=167:reason=name_token:nq|name_token:mnq|name_token:continuous|name_token:unadjusted|name_token:ohlcv|name_token:30min|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|continuous_name_bonus|unadjusted_name_bonus|ohlcv_name_bonus|2:HYDRA_RANK3_NQ_TO_MNQ_FUTURES_FAMILY_MAPPING_APPLIER_CHECKPOINT_V0_1.txt:score=133:reason=name_token:nq|name_token:mnq|name_token:futures|name_token:future|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|futures_name_bonus|3:HYDRA_RANK3_NQ_TO_MNQ_FUTURES_FAMILY_MAPPING_APPLIER_REPORT_V0_1.md:score=133:reason=name_token:nq|name_token:mnq|name_token:futures|name_token:future|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|futures_name_bonus|4:HYDRA_RANK3_NQ_TO_MNQ_FUTURES_FAMILY_MAPPING_APPROVAL_PACKET_CHECKPOINT_V0_1.txt:score=133:reason=name_token:nq|name_token:mnq|name_token:futures|name_token:future|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|futures_name_bonus|5:HYDRA_RANK3_NQ_TO_MNQ_FUTURES_FAMILY_MAPPING_APPROVAL_PACKET_REPORT_V0_1.md:score=133:reason=name_token:nq|name_token:mnq|name_token:futures|name_token:future|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|futures_name_bonus|6:HYDRA_RANK3_MNQ_CANONICAL_INGESTION_APPLIER_CHECKPOINT_V0_1.txt:score=99:reason=name_token:nq|name_token:mnq|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|7:HYDRA_RANK3_MNQ_CANONICAL_INGESTION_APPLIER_REPORT_V0_1.md:score=99:reason=name_token:nq|name_token:mnq|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|8:HYDRA_RANK3_MNQ_CANONICAL_INGESTION_POST_APPLY_VERIFIER_CHECKPOINT_V0_1.txt:score=99:reason=name_token:nq|name_token:mnq|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|9:HYDRA_RANK3_MNQ_CANONICAL_INGESTION_POST_APPLY_VERIFIER_REPORT_V0_1.md:score=99:reason=name_token:nq|name_token:mnq|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ|10:HYDRA_RANK3_MNQ_SOURCE_INGESTION_DRY_RUN_PLANNER_CHECKPOINT_V0_1.txt:score=99:reason=name_token:nq|name_token:mnq|target_name_token:NQ|target_name_token:NQ|target_name_token:MNQ`

## Counts

- pass_count: `23`
- fail_required_count: `0`
- critical_fail_count: `0`
- warning_count: `0`
- guardrail_violation_count: `0`
- scaffold_plan_rows_read: `14`
- source_boundary_contract_rows_read: `9`
- candidate_validation_contract_rows_read: `12`
- validation_evidence_contract_rows_read: `10`
- acceptance_checkpoint_contract_rows_read: `8`
- readiness_question_rows_read: `8`
- guardrail_rows_read: `53`

## Guardrails

No candidate file content read, candidate header read, candidate row read, market source read, candidate validation execution, symbol mapping, normalization transform, join, production rows, mutation, cap widening, simulation, or execution was performed.

## Next Valid Action

build/run candidate artifact validation runner execution scaffold; do not read candidate file contents until separately accepted
