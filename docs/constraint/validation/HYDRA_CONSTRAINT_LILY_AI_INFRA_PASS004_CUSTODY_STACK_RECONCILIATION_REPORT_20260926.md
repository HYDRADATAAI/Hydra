# HYDRA Constraint Lily AI infrastructure Pass004

Status: VERTICAL_INTEGRATION_THIN. Local custody/replay stack reconciliation passes; ordinary replay and native admission remain blocked.

## Result

Reapplied the Pass002/003 replay, reference-type and CI repairs to owner-seam/custody tip 1c941ad84ceb5b54c9db0eb6d055c9313ff82c88. This supersedes Pass003's failed integration trial for this exact parent. It does not supersede historical authority or declare newer mainline batches reconciled.

The old integration guard compared four Batch008 operational files to the current persisted-custody implementation as if code could never evolve. Pass004 introduces an exact four-file transition: store.py, test_store.py, README.md and pyproject.toml. The original Batch008 manifest and its old hashes are unchanged. The transition records each original and current Git blob plus the owner-stack commit. Its own blob is bound in the validator; absent, edited or self-repinned transitions fail. Current files must match the four exact successor hashes, and historical entries must retain the four exact predecessor hashes. This is a reviewable code-version reconciliation, not an authority or data-admission grant.

## Verification

166 T6 tests pass with all lineage regressions. 30 persisted T1 custody/materialization tests pass. Successor integration and owner-seam checks pass. The first-slice hostile matrix now includes seven transition attacks: deleting the transition, editing and repinning it, tampering with each of four operational files, and rewriting a historical pin. All 16 cases pass. All 23 cases in the existing NYX matrix pass separately. First-slice CI now runs the persisted T1 suite alongside the replay repair.

The original prematerialization manifest's 11 artifact hashes still match. Existing predecessor reports, masters, raw-source status, bound policies and historical manifests remain unchanged. New artifacts are validation evidence and operational transition metadata only. No private bytes are published.

## Review boundary and remaining work

This is a successor stacked draft against the current owner-seam branch, preserving PR #61 for history. Neither draft merges mainline. Physical/policy owner integration, actual private nine-source materialization, source-version lineage, native signed T5/T6 admission and full historical A–E vertical chains remain unresolved. Tests do not synthesize any of those inputs or upgrade readiness. No runtime activation, canonical promotion or V1 freeze.
