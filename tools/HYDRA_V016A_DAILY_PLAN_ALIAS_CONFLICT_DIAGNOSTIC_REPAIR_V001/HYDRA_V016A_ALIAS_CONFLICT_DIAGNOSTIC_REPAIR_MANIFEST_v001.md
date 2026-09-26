# HYDRA V016A Daily Plan Alias Conflict Diagnostic Repair V001

## Purpose

V016 correctly refused to fabricate VWAP/ONH/ONL values, but its blocked state can still be too blunt when alias values conflict or when alias columns are empty. V016A repairs that diagnostic weakness.

It performs a stricter alias pass and writes the exact alias columns and numeric values considered for each field/symbol/date target. It promotes values only when a unique high-confidence canonical/exact alias value is available in the same source CSV and the same symbol/date row.

## Hard rules

- No manual input required.
- No Hydra-root recursive scan.
- No source overwrite.
- No fabricated VWAP/ONH/ONL values.
- Only read V016 outputs and source files named by V016/V015 diagnostics.
- Do not promote generic/fuzzy alias values when exact/high-confidence aliases are absent or conflicted.
- If blocked, write exact conflict/blocker diagnostics.

## Main script

`hydra_v016a_alias_conflict_diagnostic_repair.py`

## Input

`--v016-dir` should point to the V016 output folder containing:

- `V016_POPULATION_BLOCKERS.csv`
- `run_summary_v016.json`

V016A can usually discover the V015 input folder from V016 metadata. If not, pass `--v015-dir` explicitly.

## Outputs

- `RESOLVED_FIELD_VALUES.csv` — V012/V011-compatible resolved values
- `SOURCE_COMPLETENESS_MATRIX.csv` — V012/V011-compatible completeness matrix
- `FIELD_SOURCE_CANDIDATES.csv` — compatibility output
- `SCANNED_FILES_MANIFEST.csv` — compatibility output
- `V016A_RESOLVED_FIELD_VALUES.csv`
- `V016A_ALIAS_VALUE_CANDIDATES.csv`
- `V016A_ALIAS_CONFLICT_DIAGNOSTICS.csv`
- `V016A_DECISION_AUDIT.csv`
- `V016A_POPULATION_BLOCKERS.csv`
- `V016A_PRODUCER_REPAIR_QA_REPORT.md`
- `run_summary_v016a.json`
- `run_summary_v011.json`

## Expected statuses

- `PASS_WITH_STRICT_ALIAS_VALUES`
- `PASS_WITH_PARTIAL_STRICT_ALIAS_VALUES`
- `BLOCKED_NO_SAFE_ALIAS_VALUES_DIAGNOSTICS_WRITTEN`
- `HARD_FAIL`

## Notes

If V016A blocks, the next correct lane is upstream producer/exporter code repair using the V016A conflict diagnostics. Do not patch downstream rows by hand.
