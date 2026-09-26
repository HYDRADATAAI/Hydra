# HYDRA_V020A_DAILY_PLAN_TRUE_SOURCE_FALSE_POSITIVE_REPAIR_V001

Purpose: repair V020's false-positive true-source candidate logic.

V020 incorrectly treated diagnostic metric columns such as `value_vwap_onh_onl_resolved_field_count` and `value_vwap_onh_onl_missing_field_count` as possible VWAP price values. V020A consumes V020 outputs and rejects metric/count/status/path/method/detail columns as price-field values.

Inputs:
- V020 output directory
- `TRUE_SOURCE_VALUE_CANDIDATES.csv`
- `PATCH_DECISION_MATRIX.csv`

Outputs:
- `FILTERED_TRUE_SOURCE_VALUE_CANDIDATES.csv`
- `REJECTED_V020_CANDIDATE_AUDIT.csv`
- `PATCH_DECISION_MATRIX.csv`
- `V020A_NEXT_ACTIONS.csv`
- `V020A_TRUE_SOURCE_FALSE_POSITIVE_REPAIR_QA_REPORT.md`
- `run_summary_v020a.json`

Policies:
- No manual input required
- No fake enrichment
- No Hydra root recursion
- Read-only; no producer mutation
- Reject metadata/count/status/path/detail columns as true source values
