# HYDRA Constraint semiconductor Pass010 — CI discovery repair

The Pass008/009 local test command omitted unittest's `-t .` argument. GitHub uses package-based discovery with that argument, exposing two sibling-test imports that only worked under flat discovery. Both new test modules now support package and flat discovery. The implementation is unchanged.

Verified using the exact workflow command from `constraint-t1-raw-artifact-store`: `PYTHONPATH=src python3 -m unittest discover -s tests -t . -q`. Result: 118 tests ran successfully, one environment-dependent skip.

## Inherited NYX blocker

The capture-owner base `0ef8dfb1a0be9c78a7fde88d523b65b08671404e` and this PR both contain blob `881c82941acf129e5fa2060f6d828afbbee98544` at `docs/constraint/validation/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_REAL_OUTCOME_EVIDENCE_SUPPLEMENT_REPORT_V001_20260925.md`. The existing NYX guard expects `3e26a874b98d225840d92afc52e893ea8e5e4bee` and fails.

This PR did not modify that historical report or its guard. Resolving it requires the capture-owner/mainline authority reconciliation; changing the expected hash here would conceal rather than resolve the discrepancy. The capture PR is not fully CI-green or merge-ready while this blocker remains.

No actual capture or runtime admission is claimed. Earlier passing local-test results describe flat discovery only; this report records the CI-specific correction.
