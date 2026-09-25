# HYDRA Daily Planner Review Gate - Subtask 5 Retest Quality Warnings Manual Template Patcher v0.1.1

## Result

- **Engine:** `hydra_daily_planner_review_gate_subtask5_retest_quality_warnings_manual_template_patcher_v0_1_1`
- **Version:** `v0.1.1`
- **Mode:** `CONTROLLED_SUBTASK5_RETEST_QUALITY_WARNINGS_MANUAL_INPUT_TEMPLATE_PATCHER_ONLY`
- **Overall status:** `SUBTASK5_RETEST_QUALITY_WARNINGS_MANUAL_TEMPLATE_PATCHED_READY_FOR_INTAKE_GUARD`
- **Preset:** `scaffold-smoke`
- **Template patched:** `True`
- **Ready for intake guard:** `True`
- **Generated UTC:** `2026-05-24T18:11:44+00:00`

## Guardrails

- No market-data scan
- No recursive scan
- No multi-file scan
- No planner/market join
- No level-distance calculation
- No price-reaction measurement
- No MFE/MAE calculation
- No outcome measurement
- No trade signals
- No queue mutation
- No ML labels
- No simulation
- No execution
- No external API calls
- No Asana mutation

## Required Field Summary

| Metric | Value |
|---|---:|
| Required fields | 15 |
| Populated required fields | 15 |
| Missing required fields | 0 |
| Changed fields | 15 |

## Missing Required Fields

- None

## Changed Fields

- `review_date`
- `instruments`
- `sources`
- `retest_warning_source`
- `primary_retest_quality_risk`
- `weak_retest_conditions`
- `strong_retest_conditions`
- `level_hold_requirement`
- `reclaim_reject_requirement`
- `first_touch_vs_later_touch_note`
- `compression_expansion_context`
- `no_trade_retest_conditions`
- `retest_confidence`
- `allowed_inferences`
- `not_allowed_inferences`

## Warning

The `scaffold-smoke` preset proves plumbing only. It is not a real retest-quality warning review and must not be treated as planner content.

## Next Valid Action

Rerun the Subtask 5 manual intake guard. If ready_for_materializer=True, rerun the Subtask 5 materializer with the emitted ready JSON.
