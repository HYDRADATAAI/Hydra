# HYDRA_V019A_DAILY_PLAN_PRODUCER_PATCH_COMPILE_REPAIR_V001

Purpose: repair V019's patch placement bug.

V019 inserted the validation helper before a `from __future__` import and inserted the validation call near module constants before the row variable existed. V019A creates a patched copy only, inserts the helper after the module docstring / future imports / import block, and inserts the validation call only before an actual CSV write call with a detectable row variable.

Outputs:
- V019A_PATCHED_PRIMARY_PRODUCER_COPY.py
- V019A_UNIFIED_DIFF.patch
- V019A_VALIDATION_GATE_SNIPPET.py
- V019A_SAFE_WRITE_SITE_CANDIDATES.csv
- V019A_SOURCE_SLICE_FOR_PATCH_REVIEW.csv
- V019A_PATCH_AUDIT.csv
- V019A_PATCH_BLOCKERS.csv
- V019A_PRODUCER_PATCH_QA_REPORT.md
- V019A_INSTALL_PATCH_COMMANDS_REVIEW_ONLY.ps1
- run_summary_v019a.json

Policies:
- PATCHED_COPY_ONLY_NO_ORIGINAL_MUTATION
- INSERT_HELPER_AFTER_FUTURE_IMPORTS_AND_CALL_ONLY_AT_SAFE_WRITE_SITE
- no fake VWAP / ONH / ONL values
- review-only install commands
