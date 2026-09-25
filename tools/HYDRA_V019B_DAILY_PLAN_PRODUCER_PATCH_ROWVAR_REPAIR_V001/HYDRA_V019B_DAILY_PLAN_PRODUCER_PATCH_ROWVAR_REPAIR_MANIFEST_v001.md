# HYDRA_V019B_DAILY_PLAN_PRODUCER_PATCH_ROWVAR_REPAIR_V001

Purpose: repair V019A semantic placement bug. V019A compiled, but its diff showed the validation gate called with `row_headers`, which is the header/fieldname list, not the context rows. V019B writes a patched producer copy where the validation gate must use the actual context row collection, expected as `upgraded_rows` for the V008 write.

Rules:
- no original producer mutation
- no manual input
- no fake VWAP/ONH/ONL values
- helper after shebang/docstring/__future__/import block
- validation call before actual `write_csv(..., row_headers, upgraded_rows)` write site
- block if validation uses `row_headers`, `headers`, or other fieldname list
- block if patched copy does not compile

Outputs:
- V019B_PATCHED_PRIMARY_PRODUCER_COPY.py
- V019B_UNIFIED_DIFF.patch
- V019B_VALIDATION_GATE_SNIPPET.py
- V019B_SAFE_WRITE_SITE_CANDIDATES.csv
- V019B_SOURCE_SLICE_FOR_PATCH_REVIEW.csv
- V019B_PATCH_AUDIT.csv
- V019B_PATCH_BLOCKERS.csv
- V019B_INSTALL_PATCH_COMMANDS_REVIEW_ONLY.ps1
- V019B_PRODUCER_PATCH_QA_REPORT.md
- run_summary_v019b.json
