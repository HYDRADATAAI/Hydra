# HYDRA Constraint — Batch032 Semiconductor T1 Materialization Attestation

## Result

The Batch031 Micron/TSMC-direct-provider-quarantined capture set has been
materialized and verified in the private T1 raw-artifact store.

- Release: `REL-SEMI-B031-V001`
- Release SHA-256: `c735db9e8a5daed8cff08dc7d9c2b4cc11f5910aba61669536c3961b21ac8b77`
- Immutable release-record file SHA-256: `d7a4f2f625b3a9bdd19e24204a259b68c20dea0d40e0418859d14ddea6553f8b`
- Valid source-version receipts: **30/30**
- Ordinary T2 eligible: **30/30**
- Historical availability backdated: **NO**
- Raw source bodies published to repository: **NO**
- Private filesystem paths published: **NO**

## Temporal boundary

`AVAILABLE_AT = ACQUIRED_AT` remains conservative for all 30 members.

This closes current captured-version hashes, immutable receipt custody,
release membership, and ordinary T2 eligibility.

It does **not** prove that these exact versions were available before their
capture timestamps and therefore does not by itself close strict historical
replay / required Case 12.

## Provider exclusions

The release preserves the Batch031 provider exclusion policy:

`MICRON_AND_DIRECT_TSMC_PROVIDER_CAPTURE_EXCLUDED_FROM_ACTIVE_CAPTURE`

Direct TSMC and previously quarantined Micron provider evidence remain
historical provenance records but are not active members of this release.

## Next gate

`INGEST_BATCH031_T1_RELEASE_INTO_SEMICONDUCTOR_ORDINARY_T2_NORMALIZATION`
