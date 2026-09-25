# HYDRA_V026A_DAILY_PLAN_PLATFORM_EXPORT_TARGET_FILTER_REPAIR_V001

## Purpose
Repair V026's noisy implementation target list by filtering out self/probe/diagnostic tools, derived context producers, and data/schema artifacts. Select only plausible raw platform/export emission implementation targets for source review.

## Inputs
- `--v026-dir`: Directory containing V026 outputs, especially `V026_EXPORT_IMPLEMENTATION_TARGETS.csv` and `V026_PATCH_DECISION_MATRIX.csv`.

## Outputs
- `V026A_FILTERED_PLATFORM_EXPORT_IMPLEMENTATION_TARGETS.csv`
- `V026A_EXCLUDED_EXPORT_TARGET_AUDIT.csv`
- `V026A_REPAIR_TARGET_DECISION.csv`
- `V026A_PLATFORM_EXPORT_FIELD_REQUIREMENTS.csv`
- `V026A_NEXT_ACTIONS.csv`
- `V026A_PLATFORM_EXPORT_TARGET_FILTER_QA_REPORT.md`
- `run_summary_v026a.json`

## Safety
- Read-only.
- No code or data mutation.
- No Hydra root recursion.
- No fake VWAP/ONH/ONL values.
- Keeps V019B gate as controlling downstream safety boundary.
