# HYDRA Constraint semiconductor Pass011 — inherited NYX pin reconciliation

The Batch017 outcome supplement's original commit `de10beb` contains report blob `881c82941acf129e5fa2060f6d828afbbee98544`, while its V001 manifest pins `3e26a874b98d225840d92afc52e893ea8e5e4bee`. The report has the same committed bytes on the capture-owner base and this branch. Thus the failure predates the semiconductor changes.

Added `HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH017_ARTIFACT_MANIFEST_V002_20260925.json` using the existing NYX highest-revision selection and explicit predecessor-preservation boundary. Only the report's artifact pin is corrected, to the exact blob in the original commit. The manifest records the full original commit, old pin, committed pin, affected path and reason. V001, the report, master status, outcomes and guard implementation are unchanged.

Verification: the unchanged NYX validator passes 15 manifests and 114 members, and all 19 hostile mutation cases pass. This resolves the inherited mismatch documented in Pass010 locally. GitHub CI on the new commit must still complete before a remote-green claim.

No actual source capture, semantic closure, replay admission or runtime readiness is added.
