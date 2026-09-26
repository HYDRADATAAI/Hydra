# HYDRA Constraint — Lily AI infrastructure Pass002

Final status: **VERTICAL_INTEGRATION_THIN**. Full ordinary end-to-end execution remains blocked. V1 is not frozen.

## 1. Authoritative systems reused

Work is stacked on the existing Lily owner-seam branch at `b79a853`, itself based on the T6 first-slice stack. Main was `eb193a7` at fetch. No predecessor authority/data artifact was modified. This pass changes the existing `hydra_t6_failclosed.first_slice_shadow_replay` owner, rather than adding a graph, lifecycle model, or service.

| Concept | Existing owner / integration boundary |
|---|---|
| Claims, source availability, reviewed evidence | Batch003–013 first-slice registries and conservative availability overlays |
| Actor/company/facility/geography/material/product identities | Existing first-slice IDs; physical-domain `Node`/`Edge` and `resolve_reference` inspected on separate closure branch `425ea997` |
| Capacity, dependencies, substitution | Physical-domain `Snapshot`, `Edge`, provenance and substitution-time fields; not copied into this stack |
| Source bytes and immutable source versions | Existing `constraint-t1-raw-artifact-store`; real first-slice bodies remain unmaterialized |
| T5 constraint formation and temporal/identity state | `PIPELINE_T5_CONSTRAINT_FORMATION` and Lily owner-seam candidate overlay |
| Beneficiary/canonical identity/confidence | `PIPELINE_T6_CANONICAL_CANDIDATE_GOVERNANCE`, pinned Thread-3 policy; qualification remains blocked |
| Policy/events and historical physical state | Existing `constraint-geopolitical-policy` and `constraint-physical-dependency` closure branch, not yet consumed by this first-slice stack |
| Contradictions and historical outcomes | Existing Batch012/013 scoped cases; existing outcome registries |
| Replay | Existing first-slice shadow replay repaired here; general `constraint-replay` owner inspected on separate closure branch |

Generic physical capacity supports nameplate/usable/unit, not all ten requested capacity states. Free-form attributes are not proof of governed lifecycle support. No MW-to-compute, rack-to-GPU, or production-to-available-capacity conversion was introduced.

## 2. Initial coverage audit

Classification scope is the requested AI vertical across the inspected first-slice and physical/policy closure branches. `EMPTY` means a generic owner can represent the concept but meaningful vertical population/integration was not established. `MISSING` means no dedicated governed representation or populated relationship was located in this scope; it does not authorize a parallel implementation. No requested area qualifies as FULL.

| Area | Requirement | Classification |
|---|---|---|
| Compute | data-center campuses | THIN |
| Compute | hyperscale facilities | THIN |
| Compute | colocation facilities | EMPTY |
| Compute | cloud regions | EMPTY |
| Compute | AI compute clusters | EMPTY |
| Compute | accelerator deployments | EMPTY |
| Compute | server capacity | EMPTY |
| Compute | rack-density classes where evidence permits | MISSING |
| Compute | compute expansion projects | THIN |
| Compute | facility construction/commissioning state | THIN |
| Power | generating assets | EMPTY |
| Power | generation mix | EMPTY |
| Power | grid regions | THIN |
| Power | transmission | THIN |
| Power | substations | EMPTY |
| Power | transformers | THIN |
| Power | interconnects | THIN |
| Power | interconnection queues where historically available | THIN |
| Power | contracted power | THIN |
| Power | PPAs | EMPTY |
| Power | backup generation | EMPTY |
| Power | onsite generation | THIN |
| Power | nuclear / gas / renewable dependencies | THIN |
| Power | grid congestion | THIN |
| Power | power availability constraints | THIN |
| Water / Cooling | water sources | EMPTY |
| Water / Cooling | municipal supply | EMPTY |
| Water / Cooling | cooling systems | THIN |
| Water / Cooling | water rights where strategically material | MISSING |
| Water / Cooling | drought exposure | EMPTY |
| Water / Cooling | competing industrial/municipal demand | EMPTY |
| Water / Cooling | cooling-capacity constraints | EMPTY |
| Water / Cooling | water restrictions | EMPTY |
| Semiconductor Dependency | GPU / accelerator suppliers | EMPTY |
| Semiconductor Dependency | advanced logic fabrication | EMPTY |
| Semiconductor Dependency | advanced packaging | EMPTY |
| Semiconductor Dependency | HBM | EMPTY |
| Semiconductor Dependency | memory | EMPTY |
| Semiconductor Dependency | substrates | EMPTY |
| Semiconductor Dependency | networking silicon | EMPTY |
| Semiconductor Dependency | server manufacturing | EMPTY |
| Semiconductor Dependency | critical semiconductor equipment/material dependencies | EMPTY |
| Network Infrastructure | fiber corridors | THIN |
| Network Infrastructure | carrier density | MISSING |
| Network Infrastructure | internet exchanges | EMPTY |
| Network Infrastructure | backbone connectivity | THIN |
| Network Infrastructure | subsea cable connectivity where material | EMPTY |
| Network Infrastructure | terrestrial network chokepoints | EMPTY |
| Network Infrastructure | latency-sensitive geographic relationships | MISSING |
| Physical Geography / Land | data-center clusters | THIN |
| Physical Geography / Land | industrial land | THIN |
| Physical Geography / Land | proximity to transmission | THIN |
| Physical Geography / Land | proximity to substations | EMPTY |
| Physical Geography / Land | water availability | THIN |
| Physical Geography / Land | flood/fire/weather exposure where materially relevant | EMPTY |
| Physical Geography / Land | transport/logistics dependencies | EMPTY |
| Physical Geography / Land | regional permitting constraints | THIN |

The companion audit JSON pins every inspected first-slice JSON by SHA-256. Branch separation is an integration blocker, not proof that the physical domain is absent.

## 3. Exact additions

- Repair in the existing shadow replay owner: candidate knowledge time and parent claims gate candidate visibility; missing knowledge time excludes the candidate.
- Consume the existing candidate temporal overlay explicitly. A partial/extra candidate overlay or duplicate record identity is rejected.
- Relief requires a visible parent and available referenced claims/evidence. Unknown or empty support cannot qualify.
- Beneficiary visibility requires its timestamp, parent candidate, and referenced lineage. An independent outcome observation requires its own availability and parent claim, without requiring admitted constraint formation.
- Deterministic sorted IDs; timezone-aware timestamps required.
- Extend the leak checker to inspect candidates, relief, beneficiaries and outcome lineage when full inputs are supplied. The historical two-input check remains explicitly limited.
- Fifteen adversarial regression tests, revised executable expectations, a coverage inventory, successor replay receipt, and this report.

No new real-world historical records, canonical entities, ordinary-admitted constraints, or qualified beneficiaries were minted.

## 4. Authoritative defects repaired

The predecessor `build_shadow_snapshot` included every candidate unconditionally. Its earlier window showed transformer and switchgear candidates whose referenced supplier claims were still future-known. It also showed candidates before the subsequent owner overlay's explicit knowledge time. The old `future_leaks` checked only claims/outcomes, so the receipt missed these dependencies.

The repaired owner fails closed on unknown candidate knowledge time and consumes the owner overlay without backdating it. Historical Batch011 snapshots/hashes remain unchanged as predecessor evidence. Current tests reproduce their stored hashes but no longer claim those snapshots satisfy repaired lineage semantics. No effective interval is inferred from an availability timestamp.

## 5. Vertical graph chains proven

Only normalized shadow lineage is proven: available claims → temporally visible T5 candidates → supported relief / beneficiary evaluation references. These are evaluation relationships, not qualified beneficiaries. Existing power/transformer/switchgear evidence is reused. Physical geography → energized compute → chips → policy → observed outcome has NOT been proven as one admitted traversal.

## 6. Historical replay cases

| Required replay | Current evidence | Result |
|---|---|---|
| A: semiconductor / compute | Generic semiconductor physical/policy cases exist on the separate owner branch; no integrated HBM/packaging/accelerator-to-compute chain | BLOCKED |
| B: power | Loudoun transmission and Cumulus/Susquehanna scoped evidence; transformer/switchgear shadow candidates | PARTIAL_SHADOW; ordinary replay blocked |
| C: water / cooling | Existing generic water/cooling dependence; Batch010 explicitly does not form it as a constraint | BLOCKED; no reliable facility-level water outcome assembled |
| D: technology policy | Policy owner exists on separate branch; current slice has grid-policy relief but that is not a chip export-control replay | BLOCKED |
| E: simultaneous constraints | Multiple candidates coexist; regression proves a change to one does not erase the others | STRUCTURAL_SHADOW_ONLY; no shared-cluster feasible compute calculation |

The existing ten functional case IDs are a different matrix. They cannot be relabeled A–E or counted as five successful historical vertical replays.

## 7. Lookahead attacks and results

Executed attacks cover pre-knowledge snapshots, exact overlay boundaries, future parent claims, missing candidate time, unknown/empty support, future beneficiary support, injected downstream IDs, duplicate identity, incomplete overlay, naive/invalid time, and timezone equivalence. All repaired-owner regressions pass. Timestamp availability is distinct from historical world-state validity.

Future completion, ownership, power-contract, chip-production, water-rule, network-upgrade, schedule-revision and cancellation attacks against facility lifecycle are **NOT EXECUTED**: the integrated lifecycle owner/data are not present in this stack. Generic claim filtering is not presented as those domain-specific proofs.

## 8. Contradiction / provenance results

Existing Cumulus evidence preserves development planning and approved interconnection scopes separately. Those scopes must not be averaged and are not automatically a same-measurement contradiction. Real raw-body/source-version hashes remain missing. This pass preserves references and visibility within normalized shadow artifacts, not complete T1-to-outcome provenance. No new genuine conflicting GPU-count/water/commissioning records were fabricated.

## 9. Multi-constraint results

Three candidates are visible at the reconciled knowledge boundary. Delaying transformer support excludes that candidate and its dependent beneficiary/relief without erasing unrelated candidates. Removing relief records leaves the constraints intact. This proves set independence only; no numerical achievable compute capacity, shared-facility intersection, or system-wide bottleneck resolution is claimed.

## 10. Queryability proof and limits

The existing `build_shadow_snapshot` is executable and returns five scoped ID sets. The successor receipt records four windows: before all knowledge; before supplier availability; at supplier availability; at the owner-overlay boundary. The first three cannot inherit later candidate knowledge.

| Requested query | Proof / remaining failure |
|---|---|
| Facilities by grid region | Class-level PJM/ERCOT relationships only; named facility join not proven |
| Facilities by transmission corridor | Localized reviewed case, no corridor query contract |
| Compute clusters by semiconductor supplier | Not integrated |
| Actors by HBM/packaging dependency | Not integrated |
| Power-constrained facilities at T | Candidate availability view exists; effective facility constraint query unproven |
| Facilities in water-constrained regions | Not populated/integrated |
| Substitute sites available at T | Generic relief paths exist; site-specific usable capacity unproven |
| Beneficiaries of infrastructure constraint | Four shadow evaluation references after knowledge boundary; zero qualified relationships |
| Announced but not energized at T | Distinct scoped evidence exists; lifecycle query unproven |
| All constraints on one compute cluster at T | Candidate set query exists; cluster binding and world-state validity unproven |

An unavailable query is not returned as a successful empty result. No query router or parallel graph was created to conceal these missing owner bindings.

## 11. Remaining evidence gaps

Facility-level chip/HBM/packaging dependencies; ten-state typed capacity support and lifecycle transitions; sourced site-specific water/cooling outcomes; physical network connectivity; substitution qualification, lead time/cost and capacity ceilings; contemporaneous revisions; same-cluster simultaneous constraints. GPU count unknown, water unknown, contract unknown, no-known-expansion and confirmed-no-expansion do not yet have an integrated vertical test matrix. Unknown timestamps remain unknown rather than zero/absent.

All new mutations are in test code. The production entrypoint was not activated. Production fixture isolation remains an ordinary-admission acceptance requirement; passing shadow tests does not satisfy it.

## 12. Integration failures

- Physical/policy closure and first-slice owner seams exist on separate stacks. The seam status explicitly says not to copy physical code to force convergence.
- First-slice source bodies/version hashes are absent; normalized evidence cannot substitute for immutable raw lineage.
- Native T5/T6 signed admission is absent; semantic conformance tests do not grant admission.
- Shadow replay had a downstream lookahead defect, repaired in its owning module here.
- Lifecycle, typed capacity, shared-cluster and requested query acceptance remain unproven.

## 13. Prioritized blockers

1. Integrate the existing physical/policy owner stack through normal repository review; reconcile canonical IDs and capacity/lifecycle ownership before adding AI records.
2. Materialize real sources in the existing private T1 store and bind immutable source versions; do not publish raw/private artifacts in this public branch.
3. Obtain the native T5/T6 admission evidence through its existing authority process; never synthesize it.
4. Populate bounded A/C/D/E cases and the required lifecycle/capacity/substitution semantics at their owners, then run the full facility-level attack/query matrix.

## 14. Truthful readiness and verification

**VERTICAL_INTEGRATION_THIN**. Repaired shadow availability replay is usable for its explicit scope. Ordinary replay, full provenance, governed vertical completion and a serious Constraint run remain blocked. This report is a successor scoped assessment, not a replacement T6 master or admission receipt.

Local validation: 162 T6 tests pass, including 15 new adversarial regressions. First-slice integration, owner-seam validation and the hostile-mutation matrix also pass; commands and outputs are recorded in the verification receipt. No V1 completion freeze is justified.
