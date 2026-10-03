# HYDRA CONSTRAINT — Thread 6 Successor Batch 033 Ordinary T2 Source-Version Normalization

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 032  
**Result:** `PASS_ORDINARY_T2_SOURCE_VERSION_NORMALIZATION_CURRENT_ONLY`

Batch033 closes the repo-executable source-version normalization gate declared by Batch032.

## Authority reuse

The implementation lives under the existing `constraint-t1-raw-artifact-store` owner. It adds a generic ordinary-T2 source-version lineage normalizer rather than a semiconductor-specific T2 pipeline.

Batch033 consumes only:

- the sanitized Batch032 public T1 materialization attestation; and
- the authoritative active Batch031 30-source queue.

No private raw bytes are required by the normalizer.

## Normalized lineage

The normalized packet contains exactly 30 active source versions and preserves, per member:

- `source_id`;
- `source_version_id`;
- artifact SHA-256;
- receipt SHA-256;
- source locator;
- content type / byte length;
- `ACQUIRED_AT`;
- conservative `AVAILABLE_AT`;
- ELIGIBLE disposition; and
- ordinary-T2 eligibility.

Members are deterministically sorted by `AVAILABLE_AT -> source_id -> source_version_id`.

The packet exposes cumulative conservative availability boundaries under:

`SOURCE_VISIBLE_IFF_AVAILABLE_AT_LTE_AS_OF`

## Fail-closed temporal boundary

For all 30 current captured versions:

`AVAILABLE_AT = ACQUIRED_AT`

This supports deterministic no-lookahead selection at and after those conservative timestamps.

It does **not** prove any exact source version was available before capture. Therefore:

- strict historical replay remains **NO**;
- historical availability is not backdated;
- required Case 12 remains **OPEN**.

## Authority boundary

This batch does not:

- parse or publish raw source bodies;
- promote canonical evidence claims;
- admit T5/T6 outputs;
- mint canonical constraints or beneficiaries;
- authorize the first serious Constraint run.

## Next gate

The exact reviewed semiconductor evidence records can now be bound to the normalized source versions/hashes:

`SEMICONDUCTOR_T2_EVIDENCE_LINEAGE_BINDING_FROM_BATCH033_SOURCE_VERSIONS`

```ini
THREAD6_SUCCESSOR_BATCH033=PASS
NORMALIZED_SOURCE_VERSIONS=30
ORDINARY_CURRENT_SOURCE_SET_READY=YES
CURRENT_NO_LOOKAHEAD=ENFORCED
STRICT_HISTORICAL_REPLAY_READY=NO
REQUIRED_CASES_COVERED=13/14
CASE12=OPEN
CANONICAL_EVIDENCE_ADMISSION=NO
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
```
