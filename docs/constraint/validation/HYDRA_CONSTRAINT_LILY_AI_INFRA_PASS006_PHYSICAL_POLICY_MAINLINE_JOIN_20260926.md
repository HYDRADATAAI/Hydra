# HYDRA Constraint Lily AI infrastructure Pass006

PR87 synchronization with main 35322222fe67598017eb3506ea52fb27cd00c9fa (merged physical/policy owner PR59).

GitHub initially reported dirty mergeability with outdated base metadata. A close/reopen refresh exposed the newer main. Fetching that main reproduced one real workflow conflict. Resolution retains both the replay check and all upstream custody and owner-seam checks; no validation step is removed.

The five-owner pytest importlib run then exposed a tests-package name collision in the new replay regression fixture import. Resolve the fixture by its exact sibling file using importlib, without production code changes.

Validation after repair: 312 tests and 433 subtests pass across physical dependency, geopolitical policy, historical replay, T1 custody and T6. The Pass005 four-window replay/owner-seam verifier passes. Historical masters, manifests and source data remain unchanged. Exact command:

```sh
PYTHONPATH=constraint-physical-dependency/src:constraint-geopolitical-policy/src:constraint-replay/src:constraint-t1-raw-artifact-store/src:t6-fail-closed-validator/src python -m pytest --import-mode=importlib constraint-physical-dependency/tests constraint-geopolitical-policy/tests constraint-replay/tests constraint-t1-raw-artifact-store/tests t6-fail-closed-validator/tests -q
```

This proves package coexistence and the tested replay repair, not complete facility/chip/water vertical coverage. Private raw materialization, ordinary source-version lineage and native admission remain external dependencies. No canonical promotion, ordinary replay admission or activation. Earlier receipts retain their original parent scope. Remote CI must be read for the published successor head; previous green runs are not proof for it.
