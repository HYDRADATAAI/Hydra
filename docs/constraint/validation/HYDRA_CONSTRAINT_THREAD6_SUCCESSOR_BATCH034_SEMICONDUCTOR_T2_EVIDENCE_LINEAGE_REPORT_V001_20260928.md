# HYDRA CONSTRAINT — Thread 6 Successor Batch 034 T2 Evidence Lineage Binding

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`
**Predecessor:** Batch 033
**Result:** `PASS_ACTIVE_REVIEWED_EVIDENCE_BOUND_TO_EXACT_T2_SOURCE_VERSIONS_CURRENT_ONLY`

Batch034 binds the reviewed semiconductor evidence corpus to the exact ordinary-T2 source versions normalized in Batch033.

## Inventory

Eight authoritative evidence artifacts contain **61** evidence records.

Against the active Batch031 release:

- **34** evidence records bind to active source versions;
- **27** evidence records refer only to sources outside the active release and are preserved as excluded history;
- all **30/30** active source versions have at least one bound reviewed evidence record.

The excluded records are predominantly the quarantined Micron and direct-TSMC historical evidence replaced by the successor lane.

## Exact lineage

Every active binding carries:

- evidence ID;
- source ID;
- exact source-version ID;
- artifact SHA-256;
- receipt SHA-256;
- source locator;
- originating evidence artifact;
- reviewed evidence availability, when present;
- authenticated source-version availability; and
- ordinary-T2 usable availability.

No raw source body is required or published.

## Temporal repair

All **34/34** active evidence bindings required the usable ordinary-T2 availability to be anchored at the authenticated source-version custody timestamp.

The rule is:

`ordinary_t2_available_at = max(reviewed_evidence_available_at, source_version_available_at)`

or, when the reviewed seed had no availability timestamp:

`ordinary_t2_available_at = source_version_available_at`

This prevents a manually reviewed claim from becoming replay-visible before the exact captured source version is available.

## Quarantine behavior

Evidence whose source is absent from the active 30-member release is not silently dropped and is not upgraded.

It is explicitly dispositioned as:

`SOURCE_NOT_IN_ACTIVE_RELEASE`

This preserves historical provenance while preventing quarantined Micron/direct-TSMC evidence from entering the active ordinary-T2 lane.

## What is now complete

Repository-side current custody is complete through:

```text
private raw artifact
→ immutable receipt
→ immutable release
→ public sanitized attestation
→ ordinary-T2 source-version normalization
→ exact reviewed-evidence/source-version lineage
```

## What remains blocked

This does **not** prove pre-capture availability of the exact versions.

Therefore:

- strict historical replay remains blocked;
- Case 12 remains open;
- canonical evidence admission is not self-authorized;
- T5/T6 admission is not self-authorized;
- the first serious Constraint run remains blocked.

## Stop condition

No further repository-only semiconductor custody/normalization expansion is justified by the current evidence.

The remaining gates require external historical-availability proof or authorized admission evidence.

```ini
THREAD6_SUCCESSOR_BATCH034=PASS
ACTIVE_EVIDENCE_BOUND=34
QUARANTINED_EVIDENCE_EXCLUDED=27
ACTIVE_SOURCES_WITH_BOUND_EVIDENCE=30/30
CURRENT_EVIDENCE_NO_LOOKAHEAD=ENFORCED
STRICT_HISTORICAL_REPLAY_READY=NO
REQUIRED_CASES_COVERED=13/14
CASE12=OPEN
REPO_EXECUTABLE_BLOCKERS=0
FIRST_SERIOUS_CONSTRAINT_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=NONE_CURRENT_CUSTODY_T2_NORMALIZATION_AND_EVIDENCE_LINEAGE_COMPLETE
```
