# LILY THREAD 3 — BATCH 7
## FINAL AUTHORITATIVE CONTRACT + CLOSURE LEDGER
### CANONICAL CONSTRAINT CANDIDATE + BENEFICIARY CANDIDATE

## Mission

Close Thread 3 by converting Batches 1–6 into one authoritative contract for:

- canonical constraint candidate representation;
- beneficiary candidate representation;
- identity and lifecycle state;
- evidence and derivation linkage;
- causal-chain completeness;
- merge/split/supersession lineage;
- temporal semantics;
- null/missing semantics;
- field cardinalities;
- export behavior;
- downstream guarantees;
- prohibited downstream assumptions;
- migration requirements;
- final open-question burn-down.

This batch does NOT implement validators, persistence, ranking, ML, or production ingestion.

It defines the semantic contract those systems must obey.

---

# 1. THREAD 3 OWNERSHIP — FINAL

Thread 3 owns:

1. candidate identity;
2. canonical identity;
3. merge/split semantics;
4. lifecycle semantics;
5. canonicalization state;
6. beneficiary causal-chain semantics;
7. beneficiary identity;
8. beneficiary lifecycle;
9. causal relationship semantics required for beneficiary reasoning;
10. direct-vs-derived candidate support semantics;
11. identity and beneficiary remapping after corporate/constraint changes;
12. canonical downstream handoff guarantees.

Thread 3 does NOT own:

- semantic truth conditions for what constitutes a constraint — Thread 2;
- evidence provenance/dedupe trust implementation — trust-governance layer;
- NYX validators/tests;
- ranking or trading decisions;
- Baby-ML training;
- live-source ingestion.

---

# 2. FINAL CORE DOCTRINE

Hydra must distinguish three things:

### A. INTERESTING THEME
A topic with possible economic relevance.

### B. GOVERNED CONSTRAINT CANDIDATE
A specific constraint hypothesis with governed identity, evidence lineage, temporal scope, conflict state, and lifecycle semantics.

### C. DEFENSIBLE BENEFICIARY CANDIDATE
A specific entity/constraint relationship with a complete causal chain from constraint to economically capturable value.

No promotion layer may collapse these distinctions.

---

# 3. CANONICAL DOES NOT MEAN TRUE

`canonical = governed identity/state`

NOT:

`canonical = certainly true`

Canonical candidates may be:

- disputed;
- easing;
- stale;
- moderate confidence;
- historical;
- materially degraded.

Downstream consumers MUST inspect qualifiers.

---

# 4. AUTHORITATIVE CANONICAL CONSTRAINT OBJECT

Recommended object name:

`canonical_constraint_candidate`

It represents one governed underlying constraint identity plus the current authoritative candidate state and references to full history.

---

# 5. CANONICAL CONSTRAINT — REQUIRED IDENTITY FIELDS

Required:

- `constraint_id`
- `constraint_identity_version`
- `identity_resolution_state`
- `identity_key_components`
- `identity_fingerprint`
- `identity_fingerprint_version`
- `display_name`
- `constraint_class`
- `constrained_object_id_or_key`
- `constraining_mechanism`
- `constrained_process_stage`
- `material_scope`
- `constraint_episode_id`

No canonical object is valid without all materially required identity fields resolved.

---

# 6. CANONICAL CONSTRAINT — REQUIRED GOVERNANCE FIELDS

Required:

- `promotion_state`
- `temporal_state`
- `confidence_state`
- `conflict_state`
- `degradation_state`
- `support_mode`
- `materiality_state`
- `canonical_since`
- `current_revision_id`
- `policy_version`
- `decision_provenance_id`

---

# 7. CANONICAL CONSTRAINT — REQUIRED TEMPORAL FIELDS

Required:

- `effective_from`
- `effective_to` nullable
- `observed_at` where applicable
- `available_at`
- `decision_at`
- `last_material_evidence_at`
- `last_adjudicated_at`

Historical reconstruction MUST preserve the distinction between real-world effective time and Hydra knowledge time.

---

# 8. CANONICAL CONSTRAINT — REQUIRED EVIDENCE/LINKAGE FIELDS

Required:

- `supporting_evidence_refs`
- `contradicting_evidence_refs`
- `evidence_independence_group_refs`
- `claim_refs`
- `relationship_refs`
- `derivation_refs`
- `ultimate_origin_refs`
- `source_lineage_complete`

The object may reference these through normalized child objects rather than inline arrays, but the information MUST be queryable.

---

# 9. CANONICAL CONSTRAINT — REQUIRED IDENTITY-LINEAGE FIELDS

Required or explicitly empty:

- `predecessor_constraint_ids`
- `successor_constraint_ids`
- `merge_event_refs`
- `split_event_refs`
- `supersession_event_refs`
- `parent_constraint_ids`
- `child_constraint_ids`
- `related_constraint_refs`

Empty arrays are preferred to null where the semantic answer is “none.”

---

# 10. CANONICAL CONSTRAINT — OPTIONAL FIELDS

Optional:

- `aliases`
- `constraint_family_ids`
- `severity_state`
- `persistence_state`
- `directionality_state`
- `freshness_state`
- `freshness_policy_id`
- `bindingness_state`
- `operator_notes`
- `review_flags`

Optional means absence does not make the object semantically invalid unless policy promotes the field to critical for that constraint class.

---

# 11. CANONICAL CONSTRAINT — PROHIBITED FIELDS / SEMANTICS

The canonical object MUST NOT contain fields whose semantics collapse distinct dimensions, such as:

- `truth_probability` unless a future explicitly authorized model defines it;
- `canonical_score` controlling all lifecycle behavior;
- `beneficiary_tickers` as evidence of constraint truth;
- `source_count` interpreted as corroboration;
- `active=true` derived solely from canonical state.

---

# 12. AUTHORITATIVE BENEFICIARY OBJECT

Recommended object name:

`canonical_beneficiary_candidate`

It represents one governed entity-to-constraint economic-capture relationship.

---

# 13. BENEFICIARY — REQUIRED IDENTITY FIELDS

Required:

- `beneficiary_id`
- `beneficiary_identity_version`
- `beneficiary_entity_id`
- `canonical_constraint_id`
- `beneficiary_relationship_key`
- `beneficiary_relationship_fingerprint`
- `beneficiary_relationship_fingerprint_version`
- `current_revision_id`

Beneficiary identity MUST NOT be ticker-based.

---

# 14. BENEFICIARY — REQUIRED CAUSAL-CHAIN FIELDS

Every promoted beneficiary MUST resolve:

- `needed_capability_ref`
- `critical_enabler_ref`
- `entity_exposure_ref`
- `capture_mechanism_ref`
- `capture_channel`
- `capture_temporal_window`
- `capture_materiality_state`

All five mandatory chain links from Batch 2 must be represented.

---

# 15. BENEFICIARY — REQUIRED GOVERNANCE FIELDS

Required:

- `promotion_state`
- `confidence_state`
- `conflict_state`
- `degradation_state`
- `directionality_state`
- `support_mode`
- `materiality_state`
- `upstream_constraint_authority_state`
- `policy_version`
- `decision_provenance_id`

---

# 16. BENEFICIARY — REQUIRED BLOCKER FIELDS

Required field:

`capture_blocker_refs`

It may be an empty array.

Blockers include:

- own upstream shortage;
- contract limitation;
- fixed pricing;
- unavailable capacity;
- qualification failure;
- input constraint;
- regulatory limitation;
- inability to expand;
- geographic mismatch.

A missing blocker field is invalid because downstream must distinguish “none known” from “not evaluated.”

---

# 17. BENEFICIARY — REQUIRED ENTITY ATTRIBUTION FIELDS

Required:

- `operating_entity_id`
- `economic_parent_id` nullable
- `ownership_relationship_ref` nullable
- `facility_refs`
- `security_mapping_refs`
- `economic_attribution_state`

A public ticker is never required for beneficiary validity.

---

# 18. BENEFICIARY — REQUIRED TEMPORAL FIELDS

Required:

- `effective_from`
- `effective_to` nullable
- `available_at`
- `decision_at`
- `last_material_evidence_at`
- `last_adjudicated_at`

Future capture MUST be distinguishable from current capture.

---

# 19. BENEFICIARY — REQUIRED EVIDENCE FIELDS

Required:

- `capability_evidence_refs`
- `enabler_evidence_refs`
- `exposure_evidence_refs`
- `capture_evidence_refs`
- `contradicting_evidence_refs`
- `derivation_refs`
- `ultimate_origin_refs`
- `source_lineage_complete`

---

# 20. BENEFICIARY — REQUIRED LINEAGE FIELDS

Required or explicitly empty:

- `predecessor_beneficiary_ids`
- `successor_beneficiary_ids`
- `merge_event_refs`
- `split_event_refs`
- `supersession_event_refs`
- `capture_path_refs`

---

# 21. BENEFICIARY — OPTIONAL FIELDS

Optional:

- `parent_economic_attribution_ref`
- `joint_venture_ref`
- `offtake_right_ref`
- `capacity_expansion_ref`
- `qualification_advantage_ref`
- `installed_base_advantage_ref`
- `switching_cost_ref`
- `regulatory_position_ref`
- `pricing_power_ref`
- `supply_chain_control_ref`
- `net_capture_state`
- `operator_notes`

---

# 22. REQUIRED CAUSAL CHAIN — FINAL

Every beneficiary promotion must contain:

`CONSTRAINT`
→ `NEEDED CAPABILITY`
→ `CRITICAL/SCARCE ENABLER`
→ `ENTITY EXPOSURE`
→ `ABILITY TO CAPTURE VALUE`

Missing any mandatory link means the beneficiary cannot remain canonical-current.

---

# 23. BENEFICIARY LINK CARDINALITY

A beneficiary relationship must have:

- exactly 1 canonical constraint identity;
- exactly 1 beneficiary economic actor identity;
- at least 1 needed capability;
- at least 1 critical enabler relation;
- at least 1 exposure path;
- at least 1 economically valid capture path for canonical promotion.

Multiple capture paths are allowed.

---

# 24. MULTIPLE CAPTURE PATHS

A beneficiary may possess several capture mechanisms:

- price;
- volume;
- mix;
- utilization;
- market share;
- license;
- service;
- contract duration;
- scarcity rent;
- cost advantage.

Each materially independent path SHOULD have its own governed child representation.

---

# 25. BENEFICIARY ROLLUP

The beneficiary object may remain canonical when one capture path fails if at least one complete material path remains.

All material paths failing requires re-adjudication.

---

# 26. CONSTRAINT EVIDENCE CARDINALITY

A canonical constraint must trace to:

- at least 1 admissible external evidence origin;
OR
- at least 1 admissible non-circular derivation path terminating in external evidence origins.

Zero-origin canonical candidates are prohibited.

---

# 27. DIRECT EVIDENCE NOT REQUIRED

A derived-only canonical constraint is valid if Batch 6 derivation rules are satisfied.

`support_mode = DERIVED_ONLY` MUST be visible downstream.

---

# 28. BENEFICIARY DIRECT EVIDENCE NOT REQUIRED FOR EVERY LINK

Some beneficiary links may be derived.

But every mandatory link needs admissible support, explicit derivation, and provenance closure.

---

# 29. NULL SEMANTICS — FINAL DOCTRINE

Hydra MUST distinguish:

### NULL / UNKNOWN
Value is not known or not determined.

### EMPTY
The field is evaluated and contains no members.

### NOT_APPLICABLE
The concept does not apply.

### ZERO
The quantity is known to be numerically zero.

These are not interchangeable.

---

# 30. NULL VS EMPTY ARRAY

For relationship collections:

- `[]` = evaluated and no relationships;
- `null` = unknown/not evaluated only where schema explicitly permits;
- omitted field = invalid for required fields.

Example:

`capture_blocker_refs=[]`
means evaluated, none identified.

`capture_blocker_refs=null`
means blocker evaluation unresolved, if permitted.

---

# 31. UNKNOWN MUST NOT BECOME ZERO

Unknown capacity, ownership, confidence, materiality, severity, or capture must never be converted to numeric zero.

---

# 32. NOT_APPLICABLE

Use explicit `NOT_APPLICABLE` enum/state when a concept legitimately does not apply.

Example:

pricing-power evidence may be N/A when capture mechanism is licensing.

---

# 33. REQUIRED FIELD MISSING

If a required promotion-critical field is missing:

- candidate cannot be emitted as valid canonical-current object;
- it must fail closed into watch/provisional/quarantine according to failure class.

---

# 34. OPTIONAL FIELD MISSING

Missing optional descriptive fields do not invalidate canonical status.

---

# 35. PROMOTION-CRITICAL FIELD METADATA

Schemas SHOULD mark fields as:

- `IDENTITY_CRITICAL`
- `PROMOTION_CRITICAL`
- `SUPPORTIVE`
- `DESCRIPTIVE`

This is semantic metadata, not just documentation.

---

# 36. IDENTITY-CRITICAL NULL

An unresolved identity-critical value blocks final canonical identity minting when the ambiguity could change same-vs-separate identity.

---

# 37. PROMOTION-CRITICAL NULL

An unresolved promotion-critical value blocks canonical promotion but may permit watch status.

---

# 38. SUPPORTIVE NULL

A supportive unknown may lower confidence or remove one supporting argument but does not automatically block promotion.

---

# 39. VERSIONING — OBJECT ID VS REVISION

Stable object IDs and mutable revisions are separate.

`constraint_id` remains stable across identity-preserving updates.

`constraint_revision_id` changes for material representation updates.

Same for beneficiary objects.

---

# 40. REVISION TRIGGERS — CONSTRAINT

New revision required for material changes to:

- promotion state;
- temporal state;
- confidence state;
- conflict state;
- degradation state;
- scope;
- materiality;
- support mode;
- evidence set affecting adjudication;
- causal relationships;
- lifecycle state;
- policy-driven interpretation.

---

# 41. REVISION TRIGGERS — BENEFICIARY

New revision required for material changes to:

- capture path;
- entity exposure;
- blocker state;
- materiality;
- ownership/economic attribution;
- constraint dependency;
- promotion/conflict/degradation state;
- temporal window;
- policy interpretation.

---

# 42. NON-MATERIAL METADATA UPDATE

Pure formatting/display changes MAY avoid semantic revision if governance policy treats them as presentation-only.

---

# 43. IMMUTABLE HISTORY

Historical revisions MUST be immutable.

Correction produces a new revision plus correction/supersession metadata.

---

# 44. POLICY VERSIONING

Every adjudicated state MUST reference the policy version used.

Policy changes do not silently rewrite previous decisions.

---

# 45. SCHEMA VERSIONING

Every exported object SHOULD carry:

- `schema_version`
- `policy_version`
- relevant semantic-contract version.

Schema migration and semantic re-adjudication are distinct.

---

# 46. MERGE — FINAL CONTRACT

Merge event must preserve:

- predecessor IDs;
- survivor ID;
- evidence lineage;
- contradictions;
- downstream references;
- historical validity;
- effective/decision/availability times.

No destructive merge is permitted.

---

# 47. SPLIT — FINAL CONTRACT

Split event must preserve:

- predecessor ID;
- descendant IDs;
- evidence allocation;
- beneficiary-remap state;
- historical references;
- confidence recomputation.

No confidence or beneficiary cloning.

---

# 48. SUPERSESSION — FINAL CONTRACT

Supersession means current representation has been replaced.

It does NOT mean:

- invalid;
- false;
- inactive;
- deleted.

Every superseded object MUST reference its successor(s) where applicable.

---

# 49. RETIREMENT — FINAL CONTRACT

Retirement means:

> previously valid governed candidate is no longer current/decision-relevant.

Retirement does not invalidate history.

---

# 50. REJECTION — FINAL CONTRACT

Rejection means:

> the candidate hypothesis failed semantic/evidentiary qualification for what it claimed.

Rejection must not be used simply because a valid historical constraint ended.

---

# 51. RESURRECTION — FINAL CONTRACT

Resurrection requires:

- prior retired identity;
- new post-retirement evidence;
- continuity adjudication.

If mechanism identity changed, mint a new constraint instead.

---

# 52. CONSTRAINT EPISODES

Structural identity and active episode SHOULD be separate.

One constraint may have multiple lifecycle epochs.

This supports recurrence without ID fragmentation.

---

# 53. BENEFICIARY EPISODES

A beneficiary relationship may likewise have multiple capture epochs where same entity/constraint/capture mechanism genuinely recurs.

---

# 54. CANONICAL CONSTRAINT PROMOTION STATE ENUM

Authoritative states:

- `RAW_CONSTRAINT`
- `CONSTRAINT_CANDIDATE`
- `WATCH_CANDIDATE`
- `CANONICAL_CONSTRAINT_CANDIDATE`
- `REJECTED_CANDIDATE`
- `SUPERSEDED_CANDIDATE`
- `RETIRED_CANDIDATE`
- `RESURRECTED_CANDIDATE`

---

# 55. BENEFICIARY PROMOTION STATE ENUM

Authoritative states:

- `RAW_BENEFICIARY_HYPOTHESIS`
- `BENEFICIARY_CANDIDATE`
- `WATCH_BENEFICIARY`
- `CANONICAL_BENEFICIARY_CANDIDATE`
- `REJECTED_BENEFICIARY`
- `SUPERSEDED_BENEFICIARY`
- `RETIRED_BENEFICIARY`
- `RESURRECTED_BENEFICIARY`

---

# 56. TEMPORAL STATE ENUM

Constraint temporal state SHOULD support:

- `EMERGING`
- `ACTIVE`
- `EASING`
- `DORMANT`
- `RESOLVED`
- `HISTORICAL`
- `UNKNOWN`

Promotion state and temporal state remain independent.

---

# 57. CONFIDENCE STATE ENUM

Recommended:

- `INSUFFICIENT`
- `LOW`
- `MODERATE`
- `HIGH`
- `VERY_HIGH`

This is governance/evidentiary sufficiency metadata, not probability.

---

# 58. CONFLICT STATE ENUM

Recommended:

- `NONE`
- `MINOR`
- `MATERIAL`
- `UNRESOLVED_MATERIAL`
- `SEVERE`
- `RESOLVED`

---

# 59. DEGRADATION STATE ENUM

Recommended:

- `NONE`
- `MINOR`
- `MATERIAL`
- `CRITICAL`
- `DISQUALIFYING`

---

# 60. SUPPORT MODE ENUM

Authoritative:

- `DIRECT_ONLY`
- `DERIVED_ONLY`
- `DIRECT_AND_DERIVED`
- `INSUFFICIENT`

---

# 61. MATERIALITY STATE ENUM

Recommended:

- `IMMATERIAL`
- `MINOR`
- `MATERIAL`
- `MAJOR`
- `UNKNOWN`

Constraint materiality and beneficiary capture materiality MAY use separate typed fields.

---

# 62. BENEFICIARY DIRECTIONALITY ENUM

Recommended:

- `POSITIVE_BENEFICIARY`
- `NEGATIVE_EXPOSED`
- `MIXED`
- `UNKNOWN`

---

# 63. ENTITY ATTRIBUTION STATE

Recommended:

- `RESOLVED`
- `PROVISIONAL`
- `UNRESOLVED`

Unknown attribution caps beneficiary authority.

---

# 64. IDENTITY RESOLUTION STATE

Recommended:

- `UNRESOLVED`
- `PROVISIONAL`
- `RESOLVED`
- `DISPUTED`
- `SUPERSEDED`

---

# 65. FRESHNESS STATE

Recommended:

- `FRESH`
- `SOFT_STALE`
- `HARD_STALE`
- `UNKNOWN`

Freshness does not equal truth.

---

# 66. DOWNSTREAM T6 GUARANTEE — CONSTRAINT

If Thread 3 exports a `CANONICAL_CONSTRAINT_CANDIDATE`, T6 may assume:

1. a governed stable constraint identity exists;
2. identity-critical fields satisfy current policy;
3. evidence/derivation lineage is available;
4. duplicates are not intended as independent corroboration;
5. contradiction state is explicit;
6. temporal qualifiers are explicit;
7. lifecycle state is explicit;
8. merge/split/supersession history is resolvable;
9. canonical does not imply true/active/high confidence.

---

# 67. DOWNSTREAM T6 MUST NOT ASSUME

T6 MUST NOT infer:

- canonical = true;
- canonical = active;
- canonical = high confidence;
- canonical = systemic;
- canonical = beneficiary-producing;
- evidence count = corroboration;
- missing = zero;
- retired = rejected;
- superseded = false.

---

# 68. DOWNSTREAM BENEFICIARY GUARANTEE

If Thread 3 exports a `CANONICAL_BENEFICIARY_CANDIDATE`, downstream may assume:

1. a specific governed constraint is referenced;
2. a specific governed economic actor is referenced;
3. all mandatory causal links are present;
4. at least one material capture path satisfies canonical policy;
5. blockers have been evaluated;
6. temporal overlap is governed;
7. ownership/economic attribution is explicit where relevant;
8. contradiction/degradation/materiality qualifiers are exposed;
9. lineage and provenance are resolvable.

---

# 69. DOWNSTREAM BENEFICIARY MUST NOT ASSUME

Downstream MUST NOT infer:

- beneficiary = buy;
- beneficiary = public company;
- beneficiary = positive net equity return;
- beneficiary = unconstrained entity;
- beneficiary = permanent advantage;
- beneficiary = pricing power specifically;
- beneficiary = direct supplier;
- beneficiary = high confidence merely because constraint is high confidence.

---

# 70. BABY-ML GUARANTEE — IDENTITY

Baby ML may consume only versioned observations whose:

- IDs are valid under historical information availability;
- revisions are frozen for the relevant snapshot;
- future merge/split knowledge is excluded unless an explicitly authorized corrected-history regime is used.

---

# 71. BABY-ML GUARANTEE — QUALIFIERS

Baby ML SHOULD receive separate features/states for:

- promotion;
- temporal state;
- confidence;
- conflict;
- degradation;
- support mode;
- materiality;
- missing-data state.

Do not collapse them into one scalar.

---

# 72. BABY-ML PROHIBITED ASSUMPTION

`CANONICAL = label 1`

is prohibited unless a future label contract explicitly defines that transformation.

Canonicalization is governance, not ground truth.

---

# 73. BABY-ML FUTURE-LEAKAGE GUARDRAIL

No historical observation may include:

- later merge knowledge;
- later split knowledge;
- later corporate ownership;
- later contradiction resolution;
- later direct corroboration;
- later retirement/resurrection state;

unless it was legitimately available at the reconstructed time.

---

# 74. SUPPORT GRAPH GUARANTEE

Every derived canonical candidate must trace through an acyclic support graph to external evidence origins.

---

# 75. CAUSAL GRAPH GUARANTEE

Constraint-to-constraint and constraint-to-beneficiary causal graphs MAY contain real-world cycles.

They MUST NOT be used as circular evidence.

---

# 76. IDENTITY SUCCESSION GRAPH GUARANTEE

Merge/split/supersession/refinement lineage must remain acyclic.

---

# 77. GRAPH-TYPE SEPARATION

Support graph, causal graph, and identity lineage graph are different semantic objects.

A generic unlabeled “edge” table is insufficient unless relationship type and graph semantics make the distinction unambiguous.

---

# 78. RELATIONSHIP CARDINALITY — CONSTRAINT

A constraint may have:

- zero or many parents;
- zero or many children;
- zero or many causal predecessors;
- zero or many causal successors;
- zero or many beneficiaries;
- one structural canonical identity;
- one or many lifecycle episodes.

---

# 79. RELATIONSHIP CARDINALITY — BENEFICIARY

A beneficiary relationship has:

- exactly one beneficiary actor;
- exactly one canonical constraint identity;
- one or many capability/enabler/exposure/capture links;
- zero or many blockers;
- zero or many child capture paths;
- zero or many parent-economic-attribution mappings.

---

# 80. FACILITY CARDINALITY

One beneficiary entity may control many facilities.

One facility may support many capability relationships.

Shared facility capacity must obey conservation/non-double-counting rules.

---

# 81. JOINT VENTURE CARDINALITY

One JV may have multiple owners/partners.

Economic rights and output rights must not be inferred from ownership percentage alone.

---

# 82. SECURITY CARDINALITY

One economic entity may map to zero, one, or many securities/share classes.

Security mapping is not beneficiary identity.

---

# 83. EVIDENCE CARDINALITY

One evidence artifact may support many claims/relationships.

That does not make it many independent sources.

---

# 84. DERIVATION CARDINALITY

One constraint may have multiple derivation paths.

Paths only count as independently corroborative where ultimate evidence origins are independent.

---

# 85. CONTRADICTION CARDINALITY

One candidate may have many contradictory observations.

Contradiction is preserved rather than collapsed into one boolean.

---

# 86. SOURCE COUNT PROHIBITION

No schema field called `source_count` may be used as independent corroboration without deduplicated independence semantics.

Preferred:

`independent_origin_count`

with provenance-traceable grouping.

Even that count is descriptive, not an automatic promotion rule.

---

# 87. REQUIRED TRANSITION RECORD

Every lifecycle/promotion transition must preserve:

- transition ID;
- object ID;
- old state;
- new state;
- reason code;
- effective time;
- decision time;
- available_at;
- triggering evidence/derivation refs;
- policy version;
- decision provenance.

---

# 88. REQUIRED REASON CODES

Thread 3 standard reason vocabulary SHOULD include at minimum:

- `EVIDENCE_STRENGTHENED`
- `EVIDENCE_WEAKENED`
- `EVIDENCE_INVALIDATED`
- `FRESHNESS_EXPIRED`
- `CURRENTNESS_RESTORED`
- `MATERIAL_CONTRADICTION`
- `CONTRADICTION_RESOLVED`
- `SCOPE_NARROWED`
- `SCOPE_EXPANDED`
- `IDENTITY_REVISED`
- `CONSTRAINT_RESOLVED`
- `CAPTURE_ENDED`
- `ENTITY_EXPOSURE_LOST`
- `ENTITY_EXPOSURE_GAINED`
- `MANDATORY_LINK_FAILED`
- `MANDATORY_LINK_RESTORED`
- `MATERIALITY_BELOW_GATE`
- `MATERIALITY_ABOVE_GATE`
- `SUPERSEDED_BY_MERGE`
- `SUPERSEDED_BY_SPLIT`
- `CORPORATE_ACTION`
- `RESURRECTED`

---

# 89. ANTI-FLAPPING GUARANTEE

Promotion entry may require stronger evidence than maintenance.

Hysteresis is allowed to resist noise.

It MUST NOT override:

- disqualifying evidence;
- zero admissible support;
- failed mandatory beneficiary link;
- confirmed resolution;
- identity invalidation.

---

# 90. GRACE PERIOD GUARANTEE

Grace periods may only address expected refresh lag or temporary observability gaps.

They cannot override direct disconfirmation.

---

# 91. ONE AUTHORITATIVE EVENT

One decisive high-authority event may immediately change lifecycle state.

No arbitrary multi-source confirmation requirement applies where the event itself controls reality.

---

# 92. FRESHNESS GUARANTEE

Soft/hard-stale behavior is mechanism-specific.

Hard-stale evidence alone cannot maintain current canonical authority absent durable-state justification.

---

# 93. DURABILITY OVERRIDE

A durable mechanism can extend current relevance only when the persistence basis is itself governed/evidenced.

---

# 94. IDENTITY MINTING GUARANTEE

Canonical identity may only be minted after material identity-bearing dimensions are resolved.

Do not over-specify beyond evidence.

---

# 95. IDENTITY GRANULARITY GUARANTEE

Use the narrowest stable independently meaningful bottleneck supported by evidence.

Avoid both theme buckets and article-level fragmentation.

---

# 96. PARTIAL OVERLAP GUARANTEE

Partial overlap does not default to merge.

Hydra must classify:

- same identity;
- parent/child;
- causal relation;
- shared enabler;
- compound;
- distinct;
- unresolved.

---

# 97. INDEPENDENT-RESOLUTION GUARANTEE

If two constraints can independently resolve, they normally remain separate.

---

# 98. LOCAL/SYSTEMIC GUARANTEE

Local constraints do not automatically become systemic constraints.

Systemic identity requires independent scope evidence or valid derivation.

---

# 99. COMPOUND GUARANTEE

Compound constraints are exceptional and retain constituent identities.

No theme-bucket compound is allowed.

---

# 100. TAXONOMY GUARANTEE

Taxonomy/classification changes do not themselves alter identity.

Mechanism changes may.

---

# 101. ALIAS GUARANTEE

Aliases are metadata.

They do not count as independent observations or evidence.

---

# 102. CORPORATE ACTION GUARANTEE

Ownership/economic attribution changes only at effective transfer/control time.

Announcement is not closure.

---

# 103. FACILITY GUARANTEE

Facility identity persists independently of owner identity.

Capacity must be qualified for actual use and not double-counted.

---

# 104. SHARED CAPACITY GUARANTEE

The same deployable unit of capacity cannot simultaneously satisfy multiple beneficiary/constraint claims unless allocation semantics explicitly permit it.

---

# 105. PARENT/SUBSIDIARY GUARANTEE

Operating beneficiary and parent economic attribution are separate relationships.

Full subsidiary benefit cannot be copied to parent without rights/ownership semantics.

---

# 106. JV GUARANTEE

JV capacity, economic rights, and offtake rights must remain separate.

No partner automatically receives 100% attribution.

---

# 107. DIRECT VS DERIVED GUARANTEE

Derived candidates can be canonical.

Derived outputs are not new independent evidence.

---

# 108. SUPPORT-MODE GUARANTEE

Direct, derived, and mixed support state must remain visible.

---

# 109. WEAK-EVIDENCE GUARANTEE

Multiple weak signals combine only when:

- independent enough;
- complementary enough;
- semantically sufficient through an explicit derivation.

They are not votes.

---

# 110. CAUSAL COMPOSITION GUARANTEE

Causal relationships are not universally transitive.

Composition requires governed semantics.

---

# 111. CIRCULARITY GUARANTEE

A constraint cannot support itself through descendant constraints, beneficiaries, ML predictions, market prices derived from its own hypothesis, or reingested Hydra outputs.

---

# 112. SELF-INGESTION GUARANTEE

Hydra-generated artifacts that re-enter intake must retain provenance and cannot be treated as independent external evidence.

---

# 113. BENEFICIARY MATERIALITY GUARANTEE

A beneficiary may be causally valid but economically immaterial.

Materiality is separate from causal validity.

---

# 114. BENEFICIARY UPSTREAM AUTHORITY CEILING

Current beneficiary authority ordinarily cannot exceed the current authority of the upstream constraint.

Historical/future-conditional representations are exceptions only when explicitly typed.

---

# 115. BENEFICIARY BLOCKER GUARANTEE

A strong external constraint cannot create a valid beneficiary when the entity cannot deploy/monetize the relevant capability.

---

# 116. BENEFICIARY SELF-CONSTRAINT GUARANTEE

Own constraints may:

- reduce capture;
- cap confidence;
- demote to watch;
- disqualify current capture.

---

# 117. BENEFICIARY TEMPORAL GUARANTEE

Constraint window and capture window must overlap.

Future capacity must not masquerade as current beneficiary exposure.

---

# 118. BENEFICIARY CORPORATE REMAP GUARANTEE

Acquisition, spin-off, asset sale, JV restructuring, or ownership transfer triggers re-adjudication of beneficiary attribution.

Successors do not inherit confidence automatically.

---

# 119. BENEFICIARY MERGE GUARANTEE

Constraint merge does not automatically merge beneficiary relationships.

Entity + constraint + capture mechanism must still match.

---

# 120. BENEFICIARY SPLIT GUARANTEE

Constraint split does not clone beneficiary links.

Each descendant relationship is re-adjudicated.

---

# 121. BENEFICIARY RETIREMENT GUARANTEE

Beneficiary can retire while constraint remains active.

Constraint and beneficiary lifecycle are independent.

---

# 122. BENEFICIARY REJECTION GUARANTEE

Beneficiary rejection means the causal/capture thesis failed.

It does not mean the company stopped benefiting after a previously valid period.

---

# 123. BENEFICIARY CANONICALITY GUARANTEE

Canonical beneficiary means:

> governed entity/constraint/capture relationship.

It does NOT mean:

- recommended investment;
- positive stock return;
- valuation attractiveness;
- catalyst timing;
- risk-adjusted opportunity.

---

# 124. PROHIBITED MASTER SCORE

No single scalar may determine identity, canonicalization, currentness, confidence, materiality, conflict, and beneficiary state simultaneously.

Summaries may exist downstream, but semantic dimensions remain separately governed.

---

# 125. PROHIBITED SILENT INFERENCE

Downstream systems MUST NOT invent missing semantics such as:

- unknown scope → global;
- unknown capacity → zero;
- unknown ownership → parent owns;
- canonical → active;
- supplier → beneficiary;
- price increase → pricing power;
- source repetitions → corroboration.

---

# 126. PROHIBITED DESTRUCTIVE HISTORY

No merge, split, correction, retirement, rejection, or supersession may erase prior evidence, IDs, decisions, or historical revisions required for replay/audit.

---

# 127. PROHIBITED FUTURE KNOWLEDGE

No object reconstructed as-of T may contain facts, mappings, state changes, or reconciliations available only after T.

---

# 128. EXPORT OBJECT — CURRENT VIEW

Current constraint export SHOULD include:

- canonical identity;
- current revision;
- current promotion/temporal/confidence/conflict/degradation/materiality;
- current scope;
- support mode;
- lineage pointers;
- evidence/provenance pointers;
- `available_at`;
- schema/policy versions.

---

# 129. EXPORT OBJECT — HISTORICAL VIEW

Historical export MUST support:

- as-of timestamp;
- revision valid/known at that timestamp;
- canonical identity then known;
- lifecycle state then known;
- evidence then available;
- policy then applicable.

---

# 130. CORRECTED-HISTORY VIEW

Corrected-history mapping MAY coexist with knowledge-as-of export.

It MUST be explicitly labeled and MUST NOT silently replace as-of knowledge state.

---

# 131. EXPORT OBJECT — BENEFICIARY CURRENT VIEW

Should include:

- beneficiary identity;
- canonical constraint ID;
- operating entity;
- parent attribution if any;
- mandatory causal links;
- capture paths;
- blockers;
- promotion/confidence/conflict/degradation/materiality;
- temporal window;
- lineage/provenance pointers.

---

# 132. EXPORT STABILITY

Downstream consumers may rely on stable IDs.

They MUST NOT rely on:

- stable display names;
- stable tickers;
- immutable taxonomy labels.

---

# 133. EXPORT SUPERSESSION

When an ID is superseded:

- current export follows successor;
- historical export preserves predecessor;
- reconciliation mapping remains available.

---

# 134. EXPORT SPLIT

When one ID splits:

current downstream logic MUST NOT guess the correct child.

A remap decision or unresolved state must be explicit.

---

# 135. EXPORT MERGE

When IDs merge:

current downstream may follow survivor after merge availability.

Historical knowledge-as-of views preserve prior separate IDs.

---

# 136. SCHEMA MIGRATION — LEGACY SINGLE-STATUS OBJECT

Any legacy object with only:

- `status`
- `confidence`

must migrate into separate:

- promotion state;
- temporal state;
- conflict state;
- degradation state;
- confidence state;
- materiality state.

---

# 137. SCHEMA MIGRATION — LEGACY BENEFICIARY TICKER LIST

Any representation like:

`constraint_id → [ticker1, ticker2]`

is insufficient.

Migration must create explicit beneficiary relationship objects with:

- entity identity;
- capability;
- enabler;
- exposure;
- capture mechanism;
- blockers;
- temporal/materiality state.

---

# 138. SCHEMA MIGRATION — LABEL-DERIVED CONSTRAINT ID

IDs derived from mutable names/labels must migrate to stable semantic IDs while retaining aliases and lineage.

---

# 139. SCHEMA MIGRATION — DUPLICATE CANONICAL IDS

Duplicates require explicit merge adjudication.

Do not bulk-delete duplicates based on text similarity.

---

# 140. SCHEMA MIGRATION — THEME BUCKETS

Overbroad “industry shortage” or theme-bucket IDs require split/atomic decomposition where meaningful bottlenecks differ.

---

# 141. SCHEMA MIGRATION — OVERFRAGMENTED IDS

Article-, source-, quarter-, or facility-fragmented IDs representing one bottleneck should merge while preserving original IDs/history.

---

# 142. SCHEMA MIGRATION — SOURCE COUNT

Any existing source-count confidence logic must migrate to independence-aware provenance semantics.

---

# 143. SCHEMA MIGRATION — DERIVED OBJECTS WITHOUT PREMISES

Derived constraints lacking premise/rule/origin lineage cannot be grandfathered as authoritative canonical derived objects.

They require reconstruction or demotion.

---

# 144. SCHEMA MIGRATION — BENEFICIARY WITHOUT CAPTURE

Beneficiary records missing monetization/capture logic must demote to exposure/watch/research state until causal chain is completed.

---

# 145. SCHEMA MIGRATION — CORPORATE ATTRIBUTION

Ticker/parent-only beneficiary records must migrate to operating entity + parent-economic-attribution model where possible.

---

# 146. SCHEMA MIGRATION — SHARED CAPACITY

Entity-level gross capacity used by multiple relationships must migrate to facility/capability allocation semantics to prevent double counting.

---

# 147. MIGRATION ORDER

Recommended:

1. preserve current artifacts;
2. assign schema/policy lineage;
3. normalize entity/constraint identities;
4. reconstruct provenance;
5. dedupe independence groups;
6. split overbroad identities;
7. merge duplicates;
8. construct lifecycle histories;
9. reconstruct beneficiary causal chains;
10. apply corporate/facility mappings;
11. rebuild derived support DAGs;
12. re-adjudicate canonical states;
13. validate historical replay;
14. expose downstream compatibility mapping.

---

# 148. BACKWARD COMPATIBILITY

Compatibility adapters MAY expose legacy fields temporarily.

They MUST NOT alter authoritative semantics.

Example:

legacy `is_active` may derive from temporal state, but canonical status must not be mapped into it.

---

# 149. DEPRECATION POLICY

Deprecated fields SHOULD include:

- replacement field;
- semantic warning;
- deprecation version;
- removal target if applicable.

---

# 150. FINAL MACHINE-TESTABLE GLOBAL INVARIANTS

1. Canonical never implies truth.
2. Canonical never implies active.
3. Canonical never implies high confidence.
4. Constraint identity is mechanism-based.
5. Identity and revision are separate.
6. Display names/tickers/taxonomy are not authoritative IDs.
7. Identity-critical unknowns block final canonical minting.
8. Constraint and beneficiary lifecycle are independent.
9. Retirement is not rejection.
10. Supersession is not falsity.
11. Merge never deletes predecessor history.
12. Split never clones confidence.
13. Split never clones beneficiary links automatically.
14. Duplicate evidence never counts as independent corroboration.
15. Source count is never a voting mechanism.
16. Extraction confidence is not truth probability.
17. Staleness is not resolution.
18. Missing is not zero.
19. Hard-stale evidence alone cannot support current canonicality.
20. Contradiction must be proposition/scope/time comparable.
21. Material unresolved conflict remains visible.
22. No single master score controls semantic state.
23. Derived claims are not new evidence origins.
24. Derived canonical constraints require acyclic support lineage.
25. Real-world causal cycles cannot become support cycles.
26. Hydra outputs cannot self-corroborate through reingestion.
27. Baby-ML outputs cannot bootstrap canonical truth.
28. Local constraints do not automatically imply systemic constraint.
29. Parent/child scope is not identity merge.
30. Shared enabler is not identity equivalence.
31. Compound constraints retain constituents.
32. Beneficiary requires all mandatory causal links.
33. Supplier status is insufficient for beneficiary promotion.
34. Capacity ownership is insufficient without usable/capturable exposure.
35. Demand without monetization is insufficient.
36. Scarcity without economically relevant demand is insufficient.
37. Beneficiary own-constraints can cap/disqualify capture.
38. Beneficiary current authority ordinarily cannot exceed upstream constraint authority.
39. Future capacity cannot be represented as current capture.
40. Operating beneficiary and parent attribution are separate.
41. Partial ownership does not imply full economic capture.
42. JV rights cannot be inferred solely from equity percentage.
43. Shared capacity cannot be double-counted.
44. Acquisition announcement is not ownership transfer.
45. Historical snapshots cannot contain future identity/corporate facts.
46. Constraint identity may persist across recurring episodes.
47. Same product with new limiting mechanism requires new identity.
48. Taxonomy drift alone does not create new identity.
49. Embedding similarity alone cannot merge.
50. Canonical IDs cannot be repurposed.
51. Old IDs cannot be reused.
52. Identity succession chains are acyclic.
53. Confidence is recomputed after merge/split/support changes.
54. Weak signals combine only through complementary governed logic.
55. Mandatory premise failure propagates to dependent derivation.
56. Material mandatory beneficiary-link failure forces re-adjudication.
57. Hysteresis may resist noise but not disqualifying facts.
58. Every lifecycle transition has explicit provenance.
59. Effective time and information-availability time remain separate.
60. Historical knowledge-as-of and corrected-history views are distinct.
61. Downstream must inspect qualifiers, not canonical status alone.
62. Beneficiary canonicality is not an investment recommendation.
63. Public-market tradability is not required for beneficiary identity.
64. Security mapping is separate from economic actor identity.
65. Every exported canonical object is schema/policy versioned.
66. Every derived canonical terminates in external evidence origins.
67. Unknown materiality is neither zero nor material.
68. Unknown ownership is not inferred.
69. Unknown shared-capacity allocation is not full capacity.
70. No state mutation may erase historical auditability.

---

# 151. THREAD 3 FINAL DECISION LEDGER

## DECIDED — IDENTITY
- same-underlying-constraint test;
- identity-bearing dimensions;
- independent-resolution test;
- local/systemic separation;
- identity minting;
- aliases;
- taxonomy drift;
- episode continuity;
- merge/split/supersession;
- collision resolution.

## DECIDED — LIFECYCLE
- raw;
- candidate;
- watch;
- canonical;
- rejected;
- retired;
- superseded;
- resurrected;
- degradation;
- hysteresis;
- re-promotion.

## DECIDED — EVIDENCE EFFECT
- source-quality effect;
- duplicate treatment;
- contradiction behavior;
- temporal decay;
- support mode;
- direct/derived support;
- weak-signal combination;
- derivation lineage;
- circularity prohibition.

## DECIDED — BENEFICIARY
- causal chain;
- mandatory links;
- exposure;
- monetization;
- blockers;
- materiality;
- own-constraint behavior;
- multi-path capture;
- parent/sub/JV attribution;
- corporate action remapping;
- lifecycle.

## DECIDED — DOWNSTREAM
- canonical guarantees;
- prohibited assumptions;
- export semantics;
- historical replay requirements;
- Baby-ML identity/time guardrails.

---

# 152. FINAL OPEN-QUESTION BURN-DOWN

The following are NOT unresolved Thread 3 semantic blockers:

### CLOSED
- What makes canonical different from true?
- How are duplicate constraints merged?
- When do constraints split?
- How do retired constraints resurrect?
- Can derived constraints become canonical?
- Can a beneficiary exist without direct supplier status?
- How does a company capture value?
- What if the company is itself constrained?
- What if ownership changes?
- What if capacity is shared?
- What if constraints form causal cycles?
- What if evidence is stale?
- What if state flips repeatedly?
- How are systemic constraints derived?
- How does Baby ML avoid future identity leakage?

All are closed by Batches 1–7.

---

# 153. REMAINING CROSS-THREAD QUESTIONS — NOT THREAD 3 BLOCKERS

These may require reconciliation elsewhere:

1. Exact Thread 2 semantic thresholds for when friction becomes a constraint.
2. Trust-governance implementation-specific evidence-quality enums.
3. T1/T2/T4/T5/T6 physical schema names and transport shapes.
4. NYX validator implementation and fixture design.
5. Ranking/portfolio economics.
6. Live source acquisition and parsing.
7. Baby-ML feature selection/training.
8. Production migration sequencing and performance.

Thread 3 has supplied the semantics those layers must honor.

---

# 154. THREAD 3 CLOSURE STATUS

**STATUS: SEMANTIC CONTRACT CLOSED**

Thread 3 is no longer in foundational design mode.

Future changes should be one of:

- correction;
- explicit supersession;
- cross-thread reconciliation;
- schema mapping;
- implementation clarification;
- newly discovered edge case.

New rules must cite what existing rule they extend or supersede.

---

# 155. LILY → NYX HANDOFF — FINAL

**What was decided:**  
The authoritative end-to-end canonical constraint and beneficiary semantic contract is now closed across identity, lifecycle, evidence effects, direct/derived support, beneficiary causal proof, corporate/entity attribution, shared capacity, degradation, anti-flapping, merge/split, and downstream export guarantees.

**Authoritative rules added:**  
Final object contracts; required/optional fields; field criticality; cardinalities; null/empty/unknown/zero distinctions; schema and policy versioning; current/historical export contracts; downstream assumption limits; migration order; compatibility/deprecation semantics; final global invariants.

**Rules changed/superseded:**  
No intentional reversal of Batches 1–6. Batch 7 consolidates and binds them into one contract. Where wording differs, the more specific earlier rule remains authoritative unless Batch 7 explicitly states a final rule.

**Schemas affected:**  
Canonical constraint candidate; canonical beneficiary candidate; revisions; episodes; transition events; evidence/claim/relationship references; derivation/support graph; identity lineage; facility/entity/security mapping; capacity allocation; blocker/capture paths; export envelopes; schema/policy metadata.

**Pipeline stages affected:**  
Evidence/claims/relationships → constraint candidate → canonical constraint → beneficiary candidate → canonical beneficiary → T6 exports → historical/Baby-ML observation handoff.

**New invariants:**  
The 70 final machine-testable global invariants above.

**Known ambiguity remaining:**  
No known unresolved core Thread 3 semantic blocker. Remaining questions belong primarily to Thread 2 semantic thresholds, cross-stage schema mapping, governance implementation, NYX validation, ranking, live ingestion, or Baby-ML implementation.

**Edge cases NYX should attack:**  
Canonical disputed constraint; hard-stale canonical; duplicate-source flood; duplicate canonical IDs; overbroad theme IDs; split after beneficiary promotion; merge after years of history; future acquisition leakage; JV asymmetric rights; shared-capacity double counting; derived support cycles; self-ingested Hydra output; weak-signal voting; mandatory beneficiary link unknown; beneficiary remains while constraint retires; constraint remains while beneficiary retires; recurrent episode with same mechanism; recurrent product with different mechanism.

**Expected PASS behavior:**  
Stable governed identities; explicit qualifiers; no destructive history; no fake corroboration; no circular support; no future-information leakage; complete beneficiary causal chain; explicit ownership/capacity semantics; deterministic state transitions; reproducible as-of reconstruction.

**Expected FAIL behavior:**  
Canonical interpreted as truth; ticker used as beneficiary identity; supplier automatically promoted; source-count voting; duplicate evidence inflation; scope overreach; destructive merge/split; confidence cloning; hidden mandatory-link failure; stale evidence treated as resolution; future corporate/identity facts leaked backward; Hydra/ML outputs used as self-confirming evidence.

**Migration implications:**  
Legacy schemas with collapsed status/confidence, ticker lists, label-derived IDs, duplicate canonicals, theme buckets, source-count logic, opaque derivations, parent-only attribution, or unallocated shared capacity require explicit migration before they can claim compliance with this Thread 3 contract.

**Next unresolved core-engine question:**  
**THREAD 3 CORE SEMANTICS ARE CLOSED.**  
Next work should be cross-thread reconciliation: map this contract against Thread 1 seam definitions, Thread 2 constraint semantics, Thread 4 Baby-ML contract, Thread 5 source strategy, and Thread 6 architecture decision register, then give NYX a conflict-free validation target.
