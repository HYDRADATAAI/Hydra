# HYDRA Daily Planner Review Gate - Subtask 5 Retest Quality Warnings Manual Intake Guard v0.1.1

## Result

- engine_id: `hydra_daily_planner_review_gate_subtask5_retest_quality_warnings_manual_intake_guard_v0_1_1`
- version: `v0.1.1`
- overall_status: `SUBTASK5_RETEST_QUALITY_WARNINGS_MANUAL_INPUT_READY`
- ready_for_materializer: `True`
- required_fields_count: `15`
- populated_required_count: `15`
- missing_required_count: `0`
- fail_required_count: `0`
- critical_fail_count: `0`
- warning_count: `0`

## Guardrails

- no market-data scan
- no recursive scan
- no multi-file scan
- no planner/market join
- no level-distance calculation
- no price-reaction measurement
- no MFE/MAE calculation
- no outcome measurement
- no trade signals
- no queue mutation
- no ML labels
- no simulation
- no execution
- no external API calls
- no Asana mutation

## Missing Fields

- None

## Next Valid Action

Rerun Subtask 5 materializer with the emitted manual JSON, then run/build the Subtask 5 acceptance gate.
