# HYDRA_V026_DAILY_PLAN_PLATFORM_EXPORT_CONTRACT_FIELD_POPULATION_REPAIR_V001

## Purpose
Consume V025A provenance-filter results and build a bounded platform/export field-population repair contract for VWAP_Daily, VWAP_Weekly, VWAP_Monthly, ONH, and ONL.

## Policy
- No manual input required.
- No fake enrichment.
- No downstream daily-plan rerun.
- No code/data mutation.
- No Hydra root recursion.
- Trusted values must come from raw platform/export or platform indicator output paths, not derived context/report/canonical diagnostics.

## Main script
`hydra_v026_platform_export_contract_field_population_repair.py`

## Outputs
- `V026_PLATFORM_EXPORT_CONTRACT_REPAIR_QA_REPORT.md`
- `V026_PLATFORM_EXPORT_REQUIREMENTS_CONTRACT.md`
- `V026_PLATFORM_EXPORT_FIELD_REQUIREMENTS.csv`
- `V026_TRUSTED_EXPORT_ROOT_AUDIT.csv`
- `V026_PLATFORM_EXPORT_SOURCE_AUDIT.csv`
- `V026_FIELD_VALUE_CANDIDATES.csv`
- `V026_ACCEPTED_TRUSTED_PLATFORM_EXPORT_VALUES.csv`
- `V026_REJECTED_PLATFORM_EXPORT_VALUE_AUDIT.csv`
- `V026_PATCH_DECISION_MATRIX.csv`
- `V026_EXPORT_IMPLEMENTATION_TARGETS.csv`
- `V026_NEXT_ACTIONS.csv`
- `run_summary_v026.json`

## Expected interpretation
If trusted raw export values remain missing, patch the raw platform/export emission contract next. Keep the V019B producer gate installed.
