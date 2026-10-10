# Temporary fail-closed timestamp policy

V1 receipts preserve caller-asserted acquisition and availability timestamps.
Persistence, hash integrity, release membership and ELIGIBLE disposition do not
verify acquisition time. Ordinary T2 admission is therefore disabled for all V1
receipts pending implementation of an authenticated timestamp-verification path.
This is containment, not completion of a trusted attestation system.

No verifier identities or trusted signers are added by this repair. Future
verification must bind source ID, source-version ID, artifact hash and acquisition
time to authenticated evidence and an explicitly authorized verifier. Imported
values and self-declared VERIFIED flags cannot supply that authority.

Event, publication, acquisition and known_at remain separate concepts. This repair
rewrites none of them, changes no receipt schema or stored receipt, and grants no
canonical, readiness, T1, T5/T6 or production authority. The two unresolved source
timestamps remain TIMESTAMP_UNVERIFIED. No captures or private evidence are used.

Three prior positive eligibility assertions now expect denial deliberately under
this policy; their independent storage and manifest integrity checks remain.
Windows baseline regression and repaired full-suite execution are required before
claiming closure. Python 3.11 compatibility remains unverified until tested.
# Downstream contract alignment

Materialization may complete persistence and hash binding while every V1 member
remains blocked from ordinary T2 admission. The existing eligibility/count fields
express this state; persistence success must not be treated as admission success.

Replay-lineage construction may return deterministic, non-admitting metadata for
non-quarantined materialized members. Source versions, hashes and caller-recorded
time boundaries remain bound. `ordinary_current_source_set_ready` is False and
every `eligible_source_ids` boundary is empty. `select_replay_members` rejects all
V1 selection while the trusted verifier is absent, regardless of the requested
time. Self-declared eligibility or rehashed readiness cannot reopen admission.

The V1 field set is preserved. Previously saved V1 packets that claim readiness
are rejected by the current policy; saved evidence is not rewritten. Public
attestation validation is a structural/hash check, not timestamp verification.
Historical replay, canonical admission and production readiness remain blocked.
