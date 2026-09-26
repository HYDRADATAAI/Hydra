# HYDRA V016 Daily Plan Producer Alias Population Repair V001

## Purpose

V015 proved that VWAP/ONH/ONL target columns exist in bounded producer files, but the symbol/date rows contain blank or non-numeric values. V016 performs one safe repair attempt before forcing producer-code work: it looks for populated alias columns in the same named source CSV files and emits V012-compatible resolved values if and only if the alias value is numeric and symbol/date-bound.

## Hard rules

- No manual input required.
- No Hydra-root recursive scan.
- No source overwrite.
- No fabricated VWAP/ONH/ONL values.
- Only read source files named by V015 diagnostics.
- Only promote numeric alias values from the same source CSV and same symbol/date row.
- If no alias value exists, block with explicit reason.

## Main script

`hydra_v016_producer_alias_population_repair.py`

## Input

`--v015-dir` should point to a directory containing V015 outputs, especially:

- `SOURCE_EMPTY_FIELD_AUDIT.csv`
- `POPULATION_REPAIR_TARGETS.csv`
- `PRODUCER_SOURCE_CANDIDATES.csv`

## Outputs

- `RESOLVED_FIELD_VALUES.csv` — V012-compatible resolved values
- `SOURCE_COMPLETENESS_MATRIX.csv` — V012-compatible completeness matrix
- `FIELD_SOURCE_CANDIDATES.csv` — compatibility output
- `SCANNED_FILES_MANIFEST.csv` — compatibility output
- `V016_RESOLVED_FIELD_VALUES.csv`
- `V016_PRODUCER_ALIAS_DISCOVERY.csv`
- `V016_POPULATION_REPAIR_AUDIT.csv`
- `V016_POPULATION_BLOCKERS.csv`
- `V016_PATCHED_SOURCE_MANIFEST.csv`
- `V016_PRODUCER_REPAIR_QA_REPORT.md`
- `run_summary_v016.json`
- `run_summary_v011.json`

## Expected statuses

- `PASS_WITH_ALIAS_POPULATION_VALUES`
- `PASS_WITH_PARTIAL_ALIAS_POPULATION`
- `BLOCKED_NO_ALIAS_POPULATION_VALUES_FOUND`
- `HARD_FAIL`

## Notes

If V016 returns `BLOCKED_NO_ALIAS_POPULATION_VALUES_FOUND`, the next correct lane is producer/exporter-code repair. Do not patch downstream rows by hand.
