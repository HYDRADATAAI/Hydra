# HYDRA CONSTRAINT — Lily Domain Reconciliation + Closure Report
## Historical Geography + Strategic Assets + Geology/Resource Dependency
Date: 2026-09-25
Branch: `constraint/lily-domain-reconciliation-closure-20260925`
PR: #46
Base authority stack: `constraint-geopolitical-policy-historical-batch5-20260925`

## 1. Authoritative components reused

- The existing `constraint-physical-dependency` graph remains the physical dependency representation used for resource, extraction, processing, transport, infrastructure, manufacturing, product, company/country exposure, substitution, and structural reachability. This pass did not create a replacement physical graph.
- `hydra_constraint_policy.HistoricalEvent`, `TemporalFacts`, sourced-case ingestion, and the existing policy-to-physical binding are reused for policy/conflict/disruption history.
- `hydra_constraint_replay.Evidence`, `ReplayCase`, and `replay_case()` remain the replay boundary. No second replay engine was created.
- Batch-5 replay-ready corpus controls remain in force: sourced cases stay `REPLAY_READY_UNSCORED` unless independent historical hypothesis/confidence/outcome evidence exists.
- Thread-1 frozen ownership is treated as controlling architecture: T5 owns constraint formation, T6 owns canonical constraint identity/lifecycle and beneficiary qualification, T4 trust governance owns authoritative contradiction handling, and canonical entity identity belongs to the identity authority rather than the physical graph.

## 2. Duplicate/stale components found

- The public branch stack contains three different provenance-shaped representations: physical `Provenance`, policy `Provenance`, and replay `Evidence`. They are interoperable only through adapters; the frozen T1/T2 source-version/evidence authority is not implemented as a single public owner here.
- The physical graph contains `bottleneck`, `beneficiary`, `constrains`, and `benefits` semantics. Treating these as authoritative constraint/beneficiary objects would compete with frozen T5/T6 ownership.
- `physical_adapter.py` currently permits a policy `CONSTRAINT` relation to resolve directly to a physical bottleneck or `constrains` edge. This is useful structural binding but is not sufficient proof of a T5 formed constraint.
- `claims.py` contains a useful non-adjudicating `ClaimState` model, but authoritative contradiction governance is owned by the T4 trust-governance authority. It must remain an evidence-state helper unless explicitly mapped to that owner.
- Physical `resolve_reference()` is exact-ID only. There is no canonical alias/merge/split identity history in this stack.
- The physical-layer README's original description as an isolated graph is stale relative to the now-tested policy/replay integration.

## 3. Exact reconciliation changes

Demonstrated failures were repaired without adding speculative domain categories:

1. `Snapshot.active_as_of()` now fails closed when a knowledge-bounded replay sees a snapshot with missing `known_at`.
2. `Edge.active_as_of()` now fails closed on missing `known_at` under a knowledge cutoff.
3. Identity-only nodes with no provenance no longer enter a knowledge-bounded physical replay.
4. `DependencyGraph.reference_state_as_of()` was added to preserve `PRESENT`, `ABSENT`, and `UNKNOWN` as distinct states.
5. Physical validation now rejects missing node provenance, missing edge/snapshot `known_at`, and unsupported runtime node kinds.
6. `TemporalFacts.validate()` now rejects naive semantic timestamps.
7. `active_events_as_of()` was added so known evidence can remain historically knowable while future-effective and resolved events do not remain active.
8. Regression coverage was added for missing temporal knowledge, unprovenanced identities, unknown-vs-absent behavior, unsupported geography identity, sourced Suez replay, synthetic resource-chain replay, synthetic water/energy capacity expiry, conflicting claim evidence, overlapping capacity estimates, and identical-name identity collisions.
9. No `geography` or `geology` node category was added. The test deliberately proves that an unowned `geography` kind fails validation instead of creating a shadow identity system.

## 4. Replay cases executed

### Case A — resource chain
Executed as an explicitly synthetic architecture fixture:
`deposit_source -> extraction -> processing -> transport -> infrastructure -> company -> product`, with a substitution path.
A later-known reserve estimate of 120 does not leak into the 2020 replay; the historically available estimate remains 80. Structural reachability and substitution lead time are replayable. This is an architecture proof only, not production historical evidence.

### Case B — port/chokepoint
Executed with sourced Suez 2021 evidence:
policy/disruption event -> Suez Canal physical reference -> maritime traffic -> authoritative replay evidence -> subsequent observed outcome.
The disruption is active before resolution and inactive at the resolution boundary; the physical bottleneck expires afterward.

Existing stacked suites additionally execute sourced Black Sea ports, Panama Canal water/transit, port restrictions, semiconductor controls, rare-earth disputes, LNG capacity, ownership/control, and other policy/physical cases.

### Case C — energy/water/industrial capacity
Executed as an explicitly synthetic architecture fixture:
water resource + water/power infrastructure -> manufacturing cluster -> company -> product.
A water-supply edge is present before its shutdown interval and absent afterward; the stale edge does not survive the historical graph view. This is an architecture proof only, not production historical evidence.

CI evidence on the first closure head:
- physical foundation: 6 tests, PASS;
- replay foundation: 14 tests + 22 subtests, PASS;
- policy/cross-layer integration: 82 tests, PASS;
- workflow run: `Constraint policy integration` run 36210724512, PASS.

## 5. Temporal leakage tests and results

PASS:
- later-known reserve estimate excluded from earlier replay;
- future-known physical identities excluded;
- policy events known before effective time remain knowable but are not active early;
- resolved policy events cease being active at `RESOLVED_AT`;
- expired physical bottlenecks and shutdown edges disappear after `valid_to`;
- future source availability cannot support an earlier `KNOWN_AT`;
- date-only publication handling in existing Batch-3 tests does not leak to the start of the day;
- later material identities in existing Batch-4 tests do not leak backward;
- replay-ready corpus eligibility is recomputed at every cut and must match authoritative policy eligibility.

Remaining temporal weakness:
- physical structural validity/knowledge clocks are date-granular while policy/replay clocks are timezone-aware datetimes. Same-day ordering cannot be represented with full fidelity in the physical layer.

## 6. Provenance/contradiction tests and results

PASS:
- source/evidence digest tampering fails closed;
- missing provenance fails closed;
- missing source URI fails replay adaptation;
- future-source support fails closed;
- replay corpus source bundles are pinned by Git blob SHA;
- supporting then opposing claim evidence becomes `CONTESTED` rather than being collapsed;
- two conflicting capacity snapshots (100 and 85) survive simultaneously instead of latest-row-wins collapse;
- Panama policy revision remains a modification rather than retroactive retraction;
- WTO implementation evidence remains contested rather than adjudicated.

Not proven:
- one authoritative cross-stage provenance object from source version through evidence/claim/relationship/constraint; the public stack still has multiple domain-specific provenance representations.
- a shared evidence-classification authority that makes synthetic fixture, inferred, historical, contemporary, known-absent, and disputed status first-class across every layer.

## 7. Integration failures discovered

1. **Geography/geology identity seam:** the current physical public stack has no authoritative `geography`/geology identity kind or mapping. Adding one locally would create parallel architecture, so this pass fails it closed.
2. **Canonical entity identity seam:** exact IDs resolve, but historical aliases, renames, company mergers/acquisitions, facility-name collisions, territory-name changes, identity splits, and boundary changes lack the frozen canonical identity owner implementation in this stack.
3. **Constraint ownership seam:** physical bottleneck objects and `CONSTRAINT` adapter relations can look like formed constraints, but frozen architecture assigns formation to T5. No authoritative T5 binding is implemented here.
4. **Beneficiary ownership seam:** physical `beneficiary` / `benefits` semantics are structural exposure helpers, not authoritative T6 beneficiary qualification.
5. **Contradiction ownership seam:** policy claim-state helpers preserve opposing evidence but are not the authoritative T4 trust-governance implementation.
6. **Provenance owner seam:** physical/policy/replay provenance representations are not consolidated to the frozen T1/T2 lineage authority.
7. **Full required chain:** because of items 1, 2, 3, 4, and 6, the requested geology/geography -> ... -> T5 constraint -> T6 beneficiary -> outcome chain cannot truthfully be declared end-to-end authoritative even though structural/replay portions execute.

## 8. Remaining THIN / EMPTY / MISSING areas

### THIN
- sourced physical capacity and dependency history beyond the current case bundles;
- real processing/refining, power/water, rail/port, industrial-cluster, and company/product dependency depth;
- substitution lead-time evidence;
- physical temporal precision (date rather than datetime);
- production evidence classification across domains.

### EMPTY / MISSING in this public branch stack
- authoritative geography/geology identity owner;
- canonical entity alias/merge/split/rename history;
- public implementation of the frozen T1/T2 source-version/evidence lineage owner used by all three domains;
- authoritative T5 constraint-formation integration for physical bottlenecks;
- authoritative T6 beneficiary qualification integration;
- production-sourced end-to-end Case A and Case C closures.

No new real-estate-specific architecture was found or created.

## 9. Prioritized blockers

### P0 — owner-boundary correctness
1. Bind physical bottlenecks/exposures to the authoritative T5/T6 implementations; do not let physical `bottleneck` or `beneficiary` become competing semantic owners.
2. Bind physical/policy evidence to the canonical T1/T2 provenance/lineage implementation so exact parent-version chains are provable.
3. Bind physical entity references to the canonical identity owner with point-in-time alias/merge/split/rename semantics.

### P1 — domain closure evidence
4. Implement/reuse the authoritative geography/geology identity representation rather than extending the physical graph ad hoc.
5. Add production-sourced Case A and Case C historical chains; synthetic fixtures may prove mechanics but cannot satisfy historical coverage.
6. Raise physical temporal precision where same-day order matters.
7. Add shared first-class evidence-state classification for synthetic/inferred/historical/contemporary and absence/unknown distinctions if that owner does not already exist elsewhere.

## 10. Truthful readiness status

`REPLAYABLE_WITH_BLOCKERS`

The domain is replayable through substantial physical -> policy -> replay portions, and all closure regressions pass. It is not closed because the frozen authoritative owner seams for geography/geology identity, canonical identity, provenance lineage, T5 constraint formation, and T6 beneficiary qualification are not fully integrated in this public branch stack. The remaining problem is no longer missing categories; it is owner reconciliation plus sourced coverage depth.
