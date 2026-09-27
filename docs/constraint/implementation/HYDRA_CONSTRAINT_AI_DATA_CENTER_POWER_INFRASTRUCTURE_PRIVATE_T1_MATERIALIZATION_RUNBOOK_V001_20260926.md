# HYDRA Constraint — AI/Data-Center Power First-Slice Private T1 Materialization Runbook
## Version 001 — 2026-09-26

Purpose: execute the exact nine-source raw-lineage gate without publishing third-party source bodies or inventing historical availability.

### Preconditions

- Public repository checked out locally.
- Private capture staging directory is outside the public repository.
- Private T1 raw root is outside the public repository.
- The nine reviewed source bodies have been captured through an authorized/reviewed path.
- The capture plan is copied from `HYDRA_CONSTRAINT_AI_DATA_CENTER_POWER_INFRASTRUCTURE_PRIVATE_T1_CAPTURE_PLAN_TEMPLATE_V001_20260926.json`.
- Every placeholder source-version ID, input path, and acquisition timestamp has been replaced.
- Do **not** add `available_at` to the plan. This materializer uses conservative `AVAILABLE_AT = ACQUIRED_AT`.

### Execute

From the repository root on Windows:

```powershell
$env:PYTHONPATH = "$PWD\constraint-t1-raw-artifact-store\src"

python -m hydra_constraint_t1_raw.first_slice_cli `
  --registry ".\docs\constraint\first_slice\ai_data_center_power_infrastructure_v1\HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH003_AI_DATA_CENTER_POWER_INFRASTRUCTURE_SOURCE_REGISTRY_V001_20260925.json" `
  --capture-plan "D:\HYDRA_PRIVATE\constraint\capture-plan.json" `
  --private-root "D:\HYDRA_PRIVATE\constraint\raw" `
  --public-repo-root "$PWD" `
  --attestation-output "D:\HYDRA_PRIVATE\constraint\first-slice-materialization-attestation.json"
```

The command fails closed on missing/extra sources, locator substitution, raw files inside the public repository, caller-supplied/backdated `available_at`, release timestamps before acquisition, non-persisted receipt/release authority, and quarantine-as-eligible promotion.

### Public proof after private execution

The generated attestation contains hashes and source-version metadata, not raw bytes or private paths. Validate it before adding a sanitized copy to Git:

```powershell
python .\tools\validate_constraint_t1_first_slice_attestation.py `
  --attestation "D:\HYDRA_PRIVATE\constraint\first-slice-materialization-attestation.json"
```

Expected:

```text
CONSTRAINT_T1_FIRST_SLICE_ATTESTATION=PASS
RAW_BYTES_REQUIRED_FOR_PUBLIC_VALIDATION=NO
PRIVATE_PATHS_ALLOWED_IN_ATTESTATION=NO
HISTORICAL_BACKDATING_ALLOWED=NO
```

### What this closes

A successful private execution can close first-slice raw-source materialization, immutable artifact SHA-256 capture, persisted source-version receipt identity, persisted release-manifest identity, and ordinary current T1→T2 eligibility where every source is `ELIGIBLE`.

### What this does not close

Conservative first capture does **not** prove historical availability before the capture timestamp. It therefore does not automatically close strict historical `ORIGINAL_AS_OF` replay for earlier dates, native signed T5→T6 implementation admission, canonical constraint promotion, beneficiary qualification, or first-serious-run readiness.

Historical availability requires separate provenance-bearing evidence tied to the exact source version.


### Build deterministic replay-lineage packet

After the sanitized materialization attestation validates, derive the exact
source-version/as-of membership packet without exposing raw bytes:

```powershell
python .\tools\build_constraint_t1_first_slice_replay_lineage.py `
  --attestation "D:\HYDRA_PRIVATE\constraint\first-slice-materialization-attestation.json" `
  --output "D:\HYDRA_PRIVATE\constraint\first-slice-replay-lineage-packet.json"
```

Optional deterministic membership check at a specific as-of time:

```powershell
python .\tools\build_constraint_t1_first_slice_replay_lineage.py `
  --attestation "D:\HYDRA_PRIVATE\constraint\first-slice-materialization-attestation.json" `
  --output "D:\HYDRA_PRIVATE\constraint\first-slice-replay-lineage-packet.json" `
  --as-of "2026-09-26T14:30:00Z"
```

Expected after a complete nine-source eligible capture:

```text
CONSTRAINT_T1_FIRST_SLICE_REPLAY_LINEAGE=PASS
SOURCE_VERSION_LINEAGE_COUNT=9
ORDINARY_SOURCE_VERSION_HASH_LINEAGE_COMPLETE=YES
ORDINARY_CURRENT_SOURCE_SET_READY=YES
STRICT_HISTORICAL_REPLAY_READY=NO
HISTORICAL_BACKDATING_PERFORMED=NO
```

The packet is deterministic from the sanitized attestation. It binds exact
source-version IDs, artifact/receipt hashes, release identity, and ordered
`available_at` boundaries. Its membership rule is:

`SOURCE_VISIBLE_IFF_AVAILABLE_AT_LTE_AS_OF`

This proves no-lookahead source membership for the captured lineage. It does
**not** prove that any source was available before the conservative current
capture time, so strict earlier historical replay remains blocked.
