# HYDRA_V022_DAILY_PLAN_CAPTURE_EXPORT_IMPLEMENTATION_REPAIR_LOCATOR_V001

## Purpose
V022 consumes V021 output and locates bounded upstream implementation files for the capture/export source population repair lane.

## Policy
- No Hydra root recursion.
- Uses V021 output files and V021-named paths only.
- Read-only: no code or data mutation.
- No fabricated VWAP/ONH/ONL values.
- Excludes downstream daily-plan renderer/extractor/diagnostic tools from patch target ranking.

## Inputs
- `--v021-dir`: V021 output directory.
- `--out-dir`: V022 output directory.
- Optional `--extra-code-dir`: explicit bounded directory, direct children only.

## Outputs
- `REPAIR_REQUIREMENTS.csv`
- `BOUNDED_IMPLEMENTATION_PATHS.csv`
- `CAPTURE_EXPORT_IMPLEMENTATION_CANDIDATES.csv`
- `V022_REPAIR_TARGET_SHORTLIST.csv`
- `FIELD_TO_IMPLEMENTATION_TRACE.csv`
- `CAPTURE_EXPORT_CONTRACT_FIELD_MAP.csv`
- `EXCLUDED_IMPLEMENTATION_CANDIDATE_AUDIT.csv`
- `V022_NEXT_ACTIONS.csv`
- `V022_CAPTURE_EXPORT_IMPLEMENTATION_LOCATOR_QA_REPORT.md`
- `run_summary_v022.json`

## Expected next lane
If V022 returns `PASS_WITH_CAPTURE_EXPORT_IMPLEMENTATION_TARGETS`, build V023 source review for the top shortlist target.
If blocked, provide the explicit capture/export implementation directory or file and rerun with `--extra-code-dir`.
