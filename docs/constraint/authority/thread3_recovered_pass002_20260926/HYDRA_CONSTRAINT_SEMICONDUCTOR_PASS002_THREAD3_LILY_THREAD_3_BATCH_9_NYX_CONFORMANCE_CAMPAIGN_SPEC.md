# LILY THREAD 3 — BATCH 9
## NYX CONFORMANCE CAMPAIGN SPECIFICATION
### Canonical Candidate + Beneficiary Engine

**Authority:** `LILY_THREAD_3_CANONICAL_BENEFICIARY`  
**Status:** `NYX_CONFORMANCE_CAMPAIGN_SPEC_READY`  
**Primary semantic authority:** `LILY_THREAD_3_BATCH_7_FINAL_CLOSURE.zip`  
**Primary semantic SHA-256:** `567b0fa8600f42c9885870d8b3a8bf84034000f8c72c3bff1ffccb6245e2c222`  
**Cross-thread reconciliation authority:** `LILY_THREAD_3_BATCH_8_CROSS_THREAD_RECONCILIATION.zip`  
**Reconciliation SHA-256:** `f769c02a26acdb13aea584a2e6268b389b3f1f8fe6bab4f948f5137254638f3c`

## Mission

Convert the fully closed Thread-3 semantic contract into one explicit NYX validation target.

This packet defines:

- conformance suites;
- adversarial cases;
- minimum fixture semantics;
- expected PASS behavior;
- expected FAIL behavior;
- required assertions;
- scope boundaries;
- authority pins;
- replay/time tests;
- migration tests;
- cross-thread fail-closed tests.

This packet does **NOT**:

- implement validators;
- implement fixtures;
- write test harness code;
- choose testing libraries;
- create production ingestion;
- train Baby ML;
- authorize live data;
- define unresolved Thread-2 or Trust-Governance policy.

---

# 1. CAMPAIGN AUTHORITY RULE

Every NYX campaign under this packet MUST declare:

- authority namespace;
- primary artifact;
- artifact SHA-256;
- semantic-contract version;
- cross-thread reconciliation artifact;
- test-scope identifier.

A campaign without exact authority pins is invalid.

---

# 2. CAMPAIGN SCOPE

This campaign validates Thread-3 semantics for:

1. canonical identity;
2. candidate vs canonical identity separation;
3. identity minting;
4. merge;
5. split;
6. supersession;
7. retirement;
8. rejection;
9. resurrection;
10. confidence;
11. conflict;
12. degradation;
13. materiality;
14. freshness;
15. anti-flapping;
16. direct/derived support;
17. derivation DAG;
18. weak-signal combination;
19. systemic derivation;
20. beneficiary causal chain;
21. beneficiary identity;
22. beneficiary blockers;
23. corporate actions;
24. parent/sub/JV attribution;
25. facility/shared capacity;
26. null/missing semantics;
27. versioning;
28. historical replay;
29. downstream export;
30. cross-thread authority boundaries.

---

# 3. CAMPAIGN NON-SCOPE

NYX MUST NOT treat this packet as authority for:

- exact Thread-2 semantic proof thresholds;
- exact evidence-role precedence if still owner-open;
- exact Trust-Governance numeric weighting;
- detailed contradiction reason-code taxonomy owned elsewhere;
- exact live source endpoints;
- exact ingestion cadence;
- exact Baby-ML feature visibility registry;
- database/storage implementation;
- UUID/ULID/hash choice;
- serializer ordering;
- retry library;
- test framework.

---

# 4. REQUIRED TEST RESULT TYPES

Every test case MUST resolve to one of:

- `PASS_EXPECTED`
- `FAIL_EXPECTED`
- `FAIL_CLOSED_EXPECTED`
- `DEFER_EXTERNAL_OWNER`
- `NOT_APPLICABLE`

No ambiguous “probably okay” result is permitted.

---

# 5. REQUIRED TEST RECORD FIELDS

Every NYX test case SHOULD carry:

- `test_id`
- `suite_id`
- `authority_artifact`
- `authority_sha256`
- `rule_reference`
- `input_semantics`
- `preconditions`
- `action_or_condition`
- `expected_state`
- `expected_pass_behavior`
- `expected_fail_behavior`
- `external_owner_dependency`
- `historical_time_mode`
- `severity`
- `migration_relevance`

---

# 6. SUITE T3-ID — CANONICAL IDENTITY

## Goal
Prove Hydra identifies the underlying bottleneck rather than matching words.

### T3-ID-001 — Different wording, same bottleneck
Input:
- “long lead times for large power transformers”
- “insufficient large-power-transformer manufacturing throughput”

Expected:
- same candidate/canonical identity if mechanism/stage/scope/episode match.

FAIL:
- separate IDs minted solely due to wording.

### T3-ID-002 — Same wording, different bottleneck
Input:
Two “capacity shortage” claims, one about grid transfer capacity, one about factory throughput.

Expected:
- separate identities.

FAIL:
- lexical match merges them.

### T3-ID-003 — Shared demand driver
Input:
AI demand drives power, transformer, and cooling constraints.

Expected:
- three constraint identities linked to common demand driver.

FAIL:
- one “AI infrastructure constraint” canonical ID replaces all three.

### T3-ID-004 — Same product, different mechanism
Transformer constraint caused by electrical-steel shortage vs test-bay capacity.

Expected:
- separate identities.

### T3-ID-005 — Independent-resolution test
A can resolve while B remains constrained.

Expected:
- separate identities unless explicit parent/child semantics apply.

### T3-ID-006 — Unknown mechanism
Evidence only says “semiconductor shortage.”

Expected:
- provisional/watch identity; no over-specific canonical HBM/wafer/package ID.

### T3-ID-007 — Over-specification
Evidence supports “advanced packaging shortage” but not HBM-specific shortage.

Expected:
- no HBM-specific canonical ID.

### T3-ID-008 — Under-specification
Evidence clearly distinguishes wafer-fab and packaging constraints.

Expected:
- separate canonical identities.

### T3-ID-009 — Taxonomy change only
Constraint class label changes but mechanism/object/stage remain same.

Expected:
- same `constraint_id`, new revision/classification metadata.

### T3-ID-010 — Mechanism correction
Originally “material shortage,” later proven “qualification bottleneck.”

Expected:
- identity re-adjudication; potentially new ID/supersession.

---

# 7. SUITE T3-SCOPE — LOCAL / SYSTEMIC / OVERLAP

### T3-SCOPE-001 — Three local plants
Three plants constrained.

Expected:
- three local constraints remain local.
- no systemic constraint without explicit systemic derivation.

### T3-SCOPE-002 — Valid systemic derivation
Local constraints cover material share, same mechanism, no interchangeable spare capacity.

Expected:
- separate systemic canonical identity may be derived.

### T3-SCOPE-003 — Local + systemic coexist
Expected:
- parent/child relation, not merge.

### T3-SCOPE-004 — Narrower scope
North America vs United States.

Expected:
- parent/child or same identity only if broader label was erroneous.

### T3-SCOPE-005 — Scope shrink
Global candidate later only supported regionally.

Expected:
- scope correction/split/supersession.
- not “global but lower confidence.”

### T3-SCOPE-006 — Scope expansion
Local evidence accumulates.

Expected:
- no broadening until systemic evidence/derivation exists.

---

# 8. SUITE T3-MERGE — CANONICAL MERGE

### T3-MERGE-001 — Duplicate canonicals
Two canonical IDs later proven equivalent.

Expected:
- explicit merge event;
- predecessor IDs remain resolvable;
- one survivor or explicit new survivor.

### T3-MERGE-002 — No destructive merge
Expected:
- historical candidate/evidence/contradiction lineage preserved.

### T3-MERGE-003 — Confidence recomputation
Predecessors HIGH and LOW.

Expected:
- survivor confidence recomputed.
- not HIGH by max.
- not arithmetic average.

### T3-MERGE-004 — Duplicate evidence
Both predecessors reference same press release.

Expected:
- one independence origin after merge.

### T3-MERGE-005 — Beneficiary remap
Both predecessors have same company but different capture mechanisms.

Expected:
- constraint merge does not automatically merge beneficiary relationships.

### T3-MERGE-006 — Survivor precedence
Older ID is semantically incomplete; newer ID cleanly represents reconciled identity.

Expected:
- semantic correctness wins over age.

### T3-MERGE-007 — Neither predecessor correct
Expected:
- new survivor ID; both old IDs superseded.

---

# 9. SUITE T3-SPLIT — CANONICAL SPLIT

### T3-SPLIT-001 — One broad constraint contains two mechanisms
Expected:
- predecessor superseded;
- two descendants.

### T3-SPLIT-002 — Confidence cloning prohibited
Expected:
- each child recomputes confidence.

### T3-SPLIT-003 — Beneficiary cloning prohibited
Expected:
- each beneficiary relationship re-adjudicated.

### T3-SPLIT-004 — Shared evidence
One source applies to both children.

Expected:
- may link to both, but independence does not multiply.

### T3-SPLIT-005 — Historical replay
Before split decision, ORIGINAL_AS_OF shows predecessor identity.

Expected:
- later child IDs do not leak backward.

---

# 10. SUITE T3-LIFE — LIFECYCLE

### T3-LIFE-001 — Canonical ≠ active
Canonical candidate has `temporal_state=EASING`.

Expected:
- valid.

### T3-LIFE-002 — Retired ≠ rejected
Constraint existed and later resolves.

Expected:
- `RETIRED_CANDIDATE`.

FAIL:
- `REJECTED_CANDIDATE`.

### T3-LIFE-003 — Reject invalid original hypothesis
Evidence proves claimed shortage was only demand growth.

Expected:
- rejected.

### T3-LIFE-004 — Resurrection same mechanism
Same object/mechanism/stage/scope returns after retirement.

Expected:
- same structural identity + resurrection/new episode.

### T3-LIFE-005 — Recurrence different mechanism
Same product later constrained for different reason.

Expected:
- new identity.

### T3-LIFE-006 — Superseded not reactivated
Successor weakens.

Expected:
- do not casually reactivate predecessor ID.

### T3-LIFE-007 — Easing → active
Constraint re-tightens before retirement.

Expected:
- same identity; no resurrection required.

---

# 11. SUITE T3-DEGRADE — DEGRADATION + ANTI-FLAPPING

### T3-DEGRADE-001 — One weak negative signal
Strong canonical + one weak article says improvement.

Expected:
- stay canonical, possibly warning/severity update.

### T3-DEGRADE-002 — Hard stale
No fresh current evidence beyond hard-stale threshold.

Expected:
- canonical-current authority cannot rely on stale evidence alone.
- default watch unless durable persistence is justified.

### T3-DEGRADE-003 — Missing fresh evidence
Expected:
- not automatically retired.

### T3-DEGRADE-004 — Direct resolution evidence
Authoritative source says bottleneck resolved.

Expected:
- retirement adjudication can occur immediately.

### T3-DEGRADE-005 — Identity becomes uncertain
Expected:
- watch/supersede.
- not merely lower confidence while claiming resolved identity.

### T3-DEGRADE-006 — Hysteresis
Minor alternating signals around threshold.

Expected:
- no repeated canonical↔watch flapping.

### T3-DEGRADE-007 — Hysteresis limit
Disqualifying evidence arrives.

Expected:
- state changes despite prior canonical inertia.

### T3-DEGRADE-008 — Grace period
Source refresh delayed, no contrary evidence.

Expected:
- policy-defined grace may preserve state temporarily with warning.

### T3-DEGRADE-009 — Grace cannot override contradiction
Direct contrary evidence arrives during grace.

Expected:
- grace ends / re-adjudicate.

---

# 12. SUITE T3-CONFLICT — CANDIDATE-LEVEL CONFLICT

### T3-CONFLICT-001 — Temporal update, not contradiction
January lead time 24 months; August 10 months.

Expected:
- temporal update/supersession, not necessarily contradiction.

### T3-CONFLICT-002 — Scope difference
Texas constrained; Europe unconstrained.

Expected:
- not automatically contradiction.

### T3-CONFLICT-003 — Same proposition/scope/time conflict
Two authoritative sources disagree materially.

Expected:
- `UNRESOLVED_MATERIAL` or policy-defined severe conflict;
- no source-count voting.

### T3-CONFLICT-004 — Candidate conflict vs evidence contradiction
Expected:
- candidate summary preserves references to underlying evidence-level contradiction objects.
- candidate state does not overwrite trust-governance reason taxonomy.

---

# 13. SUITE T3-EVID — DUPLICATE / INDEPENDENCE

### T3-EVID-001 — Syndication flood
Reuters → Yahoo → MSN → blog.

Expected:
- one independence origin cluster.

### T3-EVID-002 — Ten weak reposts vs one strong primary
Expected:
- count does not win.

### T3-EVID-003 — Duplicate discovered later
Previously believed independent sources share one origin.

Expected:
- recompute corroboration/confidence;
- evidence artifacts remain.

### T3-EVID-004 — Retry duplicate
Acquisition retry produces same artifact.

Expected:
- not new evidence.

---

# 14. SUITE T3-DERIVE — DIRECT / DERIVED SUPPORT

### T3-DERIVE-001 — Derived canonical allowed
Independent utilization + backlog + allocation evidence supports capacity constraint.

Expected:
- derived-only canonical allowed if rule/premises sufficient.

### T3-DERIVE-002 — Derived output is not evidence
Derived claim D generates D2/D3.

Expected:
- D2/D3 do not independently corroborate D.

### T3-DERIVE-003 — Missing mandatory premise
Expected:
- no canonical derived promotion.

### T3-DERIVE-004 — Direct support arrives later
Initially derived; later primary statement confirms.

Expected:
- same constraint identity;
- support mode becomes `DIRECT_AND_DERIVED`.

### T3-DERIVE-005 — Direct support invalidated
Derived path remains independently sufficient.

Expected:
- identity may remain; support mode becomes derived-only.

### T3-DERIVE-006 — Weak complementary signals
Utilization + backlog + allocation + capacity expansion.

Expected:
- may combine through explicit derivation.

### T3-DERIVE-007 — Weak redundant signals
Five articles repeat same lead-time claim.

Expected:
- no fake strengthening.

---

# 15. SUITE T3-DAG — SUPPORT GRAPH FIREWALL

### T3-DAG-001 — Circular support
C1 supported by C2; C2 by C3; C3 by C1.

Expected:
- FAIL.

### T3-DAG-002 — Real-world causal cycle
C1 and C2 exacerbate each other; each has independent external support.

Expected:
- PASS.

### T3-DAG-003 — Descendant self-corroboration
C1 derives C2; C2 used to corroborate C1.

Expected:
- FAIL.

### T3-DAG-004 — Hydra self-ingestion
Hydra report reingested as “new source.”

Expected:
- preserve self-origin; no independent corroboration.

### T3-DAG-005 — Baby-ML feedback
Model predicts constraint; prediction used as evidence.

Expected:
- FAIL under current contract.

### T3-DAG-006 — Beneficiary feedback
Constraint → beneficiary → stock rises → stock rise used as proof of constraint.

Expected:
- FAIL.

---

# 16. SUITE T3-TIME — DERIVATION + HISTORICAL TIME

### T3-TIME-001 — Derived available_at
Premise A available Jan 1, premise B Jan 4.

Expected:
- derived conclusion cannot be available before Jan 4.

### T3-TIME-002 — Future direct corroboration
March filing confirms January derived constraint.

Expected:
- January ORIGINAL_AS_OF remains derived-only.

### T3-TIME-003 — Future merge
Two IDs merged in June.

Expected:
- April ORIGINAL_AS_OF may show both IDs.

### T3-TIME-004 — Corrected history
Expected:
- separate explicit corrected-history view may map both to survivor.

### T3-TIME-005 — Corporate action
Deal announced January, closes June.

Expected:
- buyer parent attribution begins at effective close, not announcement.

---

# 17. SUITE T3-BEN — BENEFICIARY FIVE-LINK CHAIN

### T3-BEN-001 — Theme-only company
Constraint + same sector.

Expected:
- FAIL beneficiary promotion.

### T3-BEN-002 — Direct supplier only
Entity supplies constrained market but no capture mechanism.

Expected:
- FAIL canonical beneficiary.

### T3-BEN-003 — Valid qualified spare capacity
Constraint → needed capability → qualified spare capacity → entity exposure → volume/pricing capture.

Expected:
- PASS.

### T3-BEN-004 — Capacity without scarcity
Entity owns capacity but market has abundant substitutes.

Expected:
- FAIL constraint-derived capture.

### T3-BEN-005 — Scarcity without demand
Rare capability but no material demand.

Expected:
- FAIL.

### T3-BEN-006 — Demand without monetization
High demand, fixed price, no spare capacity, rising costs.

Expected:
- exposure may exist; beneficiary promotion fails or materially degrades.

### T3-BEN-007 — Relief provider without capture
Entity helps solve bottleneck but cannot earn incremental economics.

Expected:
- relief-provider relation allowed;
- beneficiary not implied.

### T3-BEN-008 — Substitute beneficiary
Constraint on X → adoption of Y → entity controls Y → monetization.

Expected:
- PASS if substitution/adoption timing proven.

### T3-BEN-009 — Cost-advantage beneficiary
Industry input cost rises; entity locked lower-cost supply.

Expected:
- valid capture pathway if economically material.

### T3-BEN-010 — Regulated market
No free pricing, but regulated asset-base return grows.

Expected:
- valid capture if policy/economic path explicit.

---

# 18. SUITE T3-BLOCK — BENEFICIARY BLOCKERS

### T3-BLOCK-001 — Own upstream shortage
Entity could benefit but lacks feedstock.

Expected:
- blocker reduces/caps/disqualifies capture depending severity.

### T3-BLOCK-002 — Full utilization + fixed prices
Expected:
- volume capture absent; pricing capture absent.
- no automatic benefit from full utilization.

### T3-BLOCK-003 — Full utilization + scarcity repricing
Expected:
- pricing path may remain valid.

### T3-BLOCK-004 — Qualification failure
Nameplate capacity exists but product not qualified.

Expected:
- current usable capacity does not count.

### T3-BLOCK-005 — Announced factory
Expected:
- future/watch, not current capture.

### T3-BLOCK-006 — Factory delayed beyond constraint horizon
Expected:
- future beneficiary thesis fails temporal overlap.

---

# 19. SUITE T3-BPATH — MULTIPLE CAPTURE PATHS

### T3-BPATH-001 — Pricing dies, volume survives
Expected:
- retire/supersede price path;
- beneficiary may remain canonical through volume.

### T3-BPATH-002 — Volume dies, pricing survives
Expected:
- beneficiary may remain canonical.

### T3-BPATH-003 — All paths fail
Expected:
- retire if historically valid; reject if never valid.

### T3-BPATH-004 — Three immaterial paths
Expected:
- do not automatically aggregate into material beneficiary.

---

# 20. SUITE T3-ENTITY — ENTITY / PARENT / JV

### T3-ENTITY-001 — Wholly owned subsidiary
Subsidiary operates capacity.

Expected:
- subsidiary is direct operating beneficiary;
- parent gets economic attribution.

### T3-ENTITY-002 — 60% subsidiary
Expected:
- no 100% parent capture assumption.

### T3-ENTITY-003 — Passive minority stake
Expected:
- economic interest may exist; operational control not inferred.

### T3-ENTITY-004 — 50/50 JV with asymmetric offtake
Expected:
- JV owns capacity;
- partner rights depend on actual offtake/profit rights.

### T3-ENTITY-005 — Brand vs legal entity
Expected:
- map brand to economic actor; brand alone not beneficiary ID.

### T3-ENTITY-006 — Ticker change
Expected:
- same entity/beneficiary identity if legal/economic continuity holds.

### T3-ENTITY-007 — Ticker reused by unrelated company
Expected:
- no identity continuity.

---

# 21. SUITE T3-CORP — CORPORATE ACTIONS

### T3-CORP-001 — Acquisition announced
Expected:
- future conditional mapping only.

### T3-CORP-002 — Acquisition closes
Expected:
- parent attribution changes at effective close.

### T3-CORP-003 — Failed acquisition
Expected:
- provisional future mapping terminates; no historical ownership rewrite.

### T3-CORP-004 — Spin-off
Expected:
- capability follows spun entity/rights.

### T3-CORP-005 — Asset sale
Expected:
- facility identity persists; owner attribution changes.

### T3-CORP-006 — Bankruptcy filing
Expected:
- does not automatically terminate beneficiary identity.

### T3-CORP-007 — Liquidation/asset transfer
Expected:
- old entity capture ends; successor re-adjudicated.

---

# 22. SUITE T3-CAP — FACILITY / SHARED CAPACITY

### T3-CAP-001 — One entity, two facilities
One qualified, one unqualified.

Expected:
- no blind sum.

### T3-CAP-002 — One line, two products
Switching takes six months.

Expected:
- not fully fungible to both.

### T3-CAP-003 — Shared capacity double-count
100 units claimed simultaneously for C1 and C2.

Expected:
- FAIL unless allocation semantics permit.

### T3-CAP-004 — Committed capacity
100 nameplate, 95 committed.

Expected:
- incremental capture based on applicable uncommitted capacity, not 100.

### T3-CAP-005 — Geographic mismatch
Capacity exists overseas but cannot reach target market due to regulation/logistics.

Expected:
- does not count as effective relief/capture.

---

# 23. SUITE T3-NULL — NULL / EMPTY / ZERO / N/A

### T3-NULL-001 — Unknown capacity
Expected:
- null/unknown; not zero.

### T3-NULL-002 — No blockers after evaluation
Expected:
- `capture_blocker_refs=[]`.

### T3-NULL-003 — Blockers not evaluated
Expected:
- null/unknown if schema permits; not empty array.

### T3-NULL-004 — Pricing power not applicable
Licensing capture only.

Expected:
- `NOT_APPLICABLE`, not zero.

### T3-NULL-005 — Missing required field
Expected:
- fail closed; no valid canonical-current export.

---

# 24. SUITE T3-VERS — VERSION / REVISION

### T3-VERS-001 — Confidence change
Expected:
- same ID, new revision if material.

### T3-VERS-002 — Display-name change
Expected:
- same ID; presentation metadata update/version as policy dictates.

### T3-VERS-003 — Mechanism change
Expected:
- re-adjudicate identity; do not reuse same ID blindly.

### T3-VERS-004 — Historical revision mutation
Expected:
- FAIL if prior revision overwritten.

### T3-VERS-005 — Policy change
Expected:
- prior decisions remain tied to old policy version.

---

# 25. SUITE T3-EXPORT — DOWNSTREAM CONTRACT

### T3-EXPORT-001 — Canonical with conflict
Expected:
- export valid with explicit conflict state.

### T3-EXPORT-002 — Canonical with moderate confidence
Expected:
- export valid if policy allows; downstream cannot treat as high confidence.

### T3-EXPORT-003 — Retired
Expected:
- historical/current-state semantics explicit.

### T3-EXPORT-004 — Superseded
Expected:
- successor linkage resolvable.

### T3-EXPORT-005 — Beneficiary
Expected:
- five-link chain references and blockers available.

### T3-EXPORT-006 — Public ticker absent
Expected:
- beneficiary still valid.

### T3-EXPORT-007 — Derived-only canonical
Expected:
- support mode visible.

---

# 26. SUITE T3-BML — BABY-ML BOUNDARY

### T3-BML-001 — Schema field exists
Expected:
- field not model-visible unless Thread-4 registry authorizes.

### T3-BML-002 — Future identity mapping
Expected:
- not visible in ORIGINAL_AS_OF.

### T3-BML-003 — Future contradiction resolution
Expected:
- not leaked backward.

### T3-BML-004 — Provisional transport enum
Expected:
- use Thread-3 owner meaning/version; Baby ML cannot redefine.

### T3-BML-005 — Canonical as target label
Expected:
- prohibited unless separately authorized label contract exists.

---

# 27. SUITE T3-XAUTH — CROSS-THREAD AUTHORITY

### T3-XAUTH-001 — Thread-2 unresolved semantic proof threshold
Expected:
- `DEFER_EXTERNAL_OWNER` / fail closed.
- Thread 3 does not invent it.

### T3-XAUTH-002 — Trust numeric formula absent
Expected:
- Thread 3 consumes qualitative/typed trust inputs available; does not invent formula.

### T3-XAUTH-003 — Baby-ML visibility absent
Expected:
- field masked from model use.

### T3-XAUTH-004 — Thread-5 live source not frozen
Expected:
- does not block synthetic semantic conformance tests;
- does block claims of live-source validation.

### T3-XAUTH-005 — Stale Thread-6 register
Expected:
- owner-pinned Thread-3 Batch 7 authority wins current semantic scope while preserving old register as history.

---

# 28. REQUIRED MIGRATION TESTS

NYX SHOULD include legacy migration cases for:

1. `status + confidence` collapsed schema;
2. candidate ID reused as canonical ID;
3. theme-bucket constraint;
4. one-article-per-canonical fragmentation;
5. ticker-list beneficiary representation;
6. parent-only beneficiary identity;
7. source-count confidence inflation;
8. derived object with no premise lineage;
9. no merge/split history;
10. shared capacity double counted;
11. current rows containing later canonical crosswalks;
12. null/zero conflation.

Expected migration behavior:
- preserve old artifacts;
- create explicit new semantics;
- no destructive rewrite;
- compatibility mapping where needed;
- re-adjudicate where semantic evidence is insufficient.

---

# 29. REQUIRED ADVERSARIAL COMBINATIONS

NYX SHOULD combine domains, not only test isolated rules.

### ADV-001
Duplicate canonical IDs + syndicated evidence + conflicting confidence + beneficiary links.

Expected:
- merge correctly;
- dedupe origins;
- recompute confidence;
- re-adjudicate beneficiaries.

### ADV-002
Systemic constraint derived from local plants + one unconstrained major region.

Expected:
- systemic confidence/scope affected;
- no naive local-count promotion.

### ADV-003
Canonical beneficiary + acquisition closes + constraint splits.

Expected:
- ownership remap and constraint-child remap both explicit;
- no automatic cloning.

### ADV-004
Derived-only canonical + hard-stale premises + one fresh contradictory primary source.

Expected:
- current authority degrades/fails closed appropriately.

### ADV-005
JV capacity + asymmetric offtake + shared capacity across two constraints.

Expected:
- no 100% allocation to each partner or each constraint.

### ADV-006
Retired constraint resurrects + facility has new owner.

Expected:
- same constraint identity may resurrect;
- beneficiary actor re-adjudicated to new owner.

### ADV-007
Baby-ML historical snapshot before later merge/split/corporate action.

Expected:
- no future leakage.

---

# 30. MINIMUM ACCEPTANCE GATES

Thread-3 semantic conformance SHOULD NOT be declared PASS unless all critical suites pass:

- `T3-ID`
- `T3-MERGE`
- `T3-SPLIT`
- `T3-LIFE`
- `T3-DERIVE`
- `T3-DAG`
- `T3-TIME`
- `T3-BEN`
- `T3-BLOCK`
- `T3-ENTITY`
- `T3-CAP`
- `T3-NULL`
- `T3-EXPORT`
- `T3-XAUTH`

Other suites may be classified separately by policy, but no critical semantic failure may be masked by aggregate score.

---

# 31. NO MASTER PASS SCORE

NYX MUST NOT reduce Thread-3 conformance to:

`92% tests passed = compliant`

if any critical invariant fails.

Certain failures are release-blocking regardless of aggregate percentage:

- ID reuse;
- destructive merge/split;
- circular support;
- future leakage;
- canonical=truth;
- beneficiary without mandatory causal chain;
- shared-capacity double counting;
- missing=zero;
- self-ingestion as independent evidence.

---

# 32. REQUIRED FAILURE SEVERITY

Recommended:

- `CRITICAL_CONTRACT_VIOLATION`
- `MAJOR_SEMANTIC_VIOLATION`
- `MINOR_COMPATIBILITY_DRIFT`
- `EXTERNAL_OWNER_OPEN`
- `NON_SEMANTIC_IMPLEMENTATION_VARIANCE`

---

# 33. CRITICAL CONTRACT VIOLATIONS

Always critical:

1. canonical ID reuse;
2. evidence/history deletion;
3. future-knowledge leakage;
4. support DAG cycle;
5. Hydra self-corroboration;
6. beneficiary promoted without mandatory chain;
7. unknown converted to zero where meaning changes;
8. T5 directly minting canonical identity;
9. Baby ML redefining upstream semantics;
10. shared deployable capacity double-counted as independent capacity.

---

# 34. EXPECTED PASS REPORT

A compliant NYX report SHOULD identify:

- artifact pins;
- suites executed;
- cases passed;
- fail-closed cases;
- external-owner deferred cases;
- critical violations;
- compatibility drift;
- migration-only failures;
- historical replay status;
- final scoped conclusion.

---

# 35. EXPECTED FINAL SCOPED CONCLUSION

Valid examples:

`THREAD3_SEMANTIC_CONFORMANCE = PASS`

`THREAD3_SEMANTIC_CONFORMANCE = FAIL_CRITICAL`

`THREAD3_SEMANTIC_CONFORMANCE = PASS_WITH_EXTERNAL_OWNER_DEFERRED_ITEMS`

Invalid:

`Hydra fully production ready`

This campaign does not validate live ingestion or full-system production readiness.

---

# 36. LILY → NYX HANDOFF

## What was decided
- The complete Thread-3 semantic contract has been converted into a concrete NYX test campaign specification.
- The campaign is artifact-pinned to Batch 7 and Batch 8.
- Critical suites and critical invariant failures are identified.
- Cross-thread unresolved owner semantics fail closed rather than being guessed.
- Conformance percentage cannot hide critical semantic violations.
- Historical replay, circularity, beneficiary causality, capacity conservation, and identity integrity are mandatory attack surfaces.

## Authoritative rules added
No new core Thread-3 semantic rules.
This batch adds only validation scope, case taxonomy, expected behavior, and acceptance structure.

## Rules changed/superseded
None.

## Schemas affected
NYX test-case metadata, campaign result metadata, migration classification, authority pinning.

## Pipeline stages affected
Validation only. No runtime ownership changes.

## Known ambiguity remaining
No core Thread-3 semantic ambiguity.
Unresolved upstream-owner semantics remain external dependencies and must stay explicitly deferred/fail-closed.

## Edge cases NYX should attack
All suites and adversarial combinations above.

## Expected PASS behavior
Thread-3 semantics are preserved under adversarial identity, lifecycle, derivation, beneficiary, corporate, capacity, null, and historical-time scenarios.

## Expected FAIL behavior
Any implementation invents truth from canonicality, destroys lineage, manufactures corroboration, guesses unresolved ownership/scope, leaks future facts, or promotes beneficiaries without economic-capture proof.

## Migration implications
Legacy artifacts that cannot satisfy the closed semantics must be migrated or explicitly marked nonconformant; they are not grandfathered into compliance.

## Next unresolved core-engine question
None inside Thread 3.

Next action:
**NYX executes the campaign.**
Lily should only return for:
- semantic interpretation dispute;
- genuine cross-thread contradiction;
- explicit supersession request;
- newly discovered edge case.
