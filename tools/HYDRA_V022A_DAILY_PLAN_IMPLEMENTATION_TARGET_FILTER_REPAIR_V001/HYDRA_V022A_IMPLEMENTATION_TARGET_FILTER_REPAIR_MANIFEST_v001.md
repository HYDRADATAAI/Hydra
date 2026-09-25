# HYDRA_V022A_DAILY_PLAN_IMPLEMENTATION_TARGET_FILTER_REPAIR_V001

## Purpose
Repair V022's over-broad capture/export implementation locator output by filtering out data outputs, schema audits, reports, and downstream daily-plan tools before selecting the next source-review target.

## Files
- `hydra_v022a_implementation_target_filter_repair.py`
- `run_v022a_windows.ps1`
- `HYDRA_V022A_IMPLEMENTATION_TARGET_FILTER_REPAIR_MANIFEST_v001.md`

## Policy
- No Hydra root recursion.
- Reads V022 outputs only.
- Read-only: no code/data mutation.
- No fake VWAP/ONH/ONL values.
- Does not recommend CSV/JSON/MD reports as patch targets.

## Expected outputs
- `V022A_FILTERED_IMPLEMENTATION_SHORTLIST.csv`
- `V022A_EXCLUDED_TARGET_AUDIT.csv`
- `V022A_REPAIR_TARGET_DECISION.csv`
- `V022A_NEXT_ACTIONS.csv`
- `V022A_IMPLEMENTATION_TARGET_FILTER_QA_REPORT.md`
- `run_summary_v022a.json`
