# RECRUITER_SCAN_PATH_AUDIT

**Pass:** W6 — Recruiter Scan Test  
**Audit basis:** Latest known HYDRA V7 recruiter-facing site state. This pass does **not** assume W1–W5 changes running in parallel have already been merged.  
**Scope rule:** Record friction, fix only high-value scan friction, do not redesign the site.

## Executive result

| Reader | Result | Core finding |
|---|---|---|
| Reader A — Recruiter, 30 seconds | **PASS_WITH_MINOR_FRICTION** | HYDRA's purpose and technical territory are immediately legible. The builder's engineering identity is strongly implied as data engineering, but not stated as directly as the platform identity. |
| Reader B — Engineering manager, 2 minutes | **PASS_WITH_HIGH_VALUE_EVIDENCE_FRICTION** | Architecture, contract/authority enforcement, provenance, release behavior, and the defect/blocking philosophy are understandable. The weak point is jumping from explanation to directly inspectable technical evidence. |
| Reader C — Engineer, 5–10 minutes | **PARTIAL — BLOCKED_AT_SOURCE_INSPECTION** | The site provides the conceptual trail and representative case study, but the current public path to schemas, transformations, test artifacts, lineage receipts, and runnable/inspectable source material is not yet strong enough. |

**Overall:** The storefront works. The proof-room door needs a brighter handle.

---

## Reader A — Recruiter, 30 seconds

**Expected path:** Homepage hero → approved capability badges → architecture/data-flow visual → first proof-oriented section.

| Question | Result | Scan finding |
|---|---|---|
| What is HYDRA? | **PASS** | “HYDRA / MARKET INTELLIGENCE DATA PLATFORM” plus “Turn fragmented market data into traceable intelligence” answers this almost immediately. |
| What kind of engineer built it? | **PARTIAL** | The work clearly reads as data-platform/data-engineering work through ingestion, contracts, lineage, and release gates. The reader still has to infer the engineering discipline instead of being handed one concise label. |
| What technical areas does it demonstrate? | **PASS** | Multi-source ingestion, contract-bound handoffs, lineage, release gates, identity/authority handling, market constraint intelligence, and testing/integrity are visible enough for a quick scan. |

### Reader A friction

| ID | Severity | Friction | Action |
|---|---:|---|---|
| A-01 | Medium | Engineering discipline is inferred rather than stated directly. | Add one non-hero line near the first proof section: **“Engineering focus: data ingestion, contract validation, provenance/lineage, integration testing, and market constraint intelligence.”** |
| A-02 | Low | The site has enough technical material that a recruiter could overscan instead of following one obvious proof path. | Let the W2 proof strip become the default first technical path. Do not add more homepage explanation. |

**Reader A target after fix:** all three questions answerable within the hero plus one short scroll.

---

## Reader B — Engineering manager, 2 minutes

**Expected path:** Homepage → Architecture → Engineering Proof → Integrity/Admissibility example → representative constraint case.

| Question | Result | Scan finding |
|---|---|---|
| What is the architecture? | **PASS** | The Market → reference → history → contract gate → data core → lineage → query/intelligence flow gives the manager a coherent system picture. |
| How is data quality enforced? | **PASS** | Contract-bound handoffs, authority checks, release gates, and the “block rather than fabricate” behavior form a credible quality-control story. |
| How is provenance handled? | **PASS** | Lineage/history is part of the architecture and the representative case follows evidence through governed stages rather than presenting an unexplained final answer. |
| How does testing work? | **PARTIAL** | The site communicates test-first behavior and named failure/blocking behavior, but the scan still needs one compact, unmistakable real test receipt with input → result → defect/block → rerun or stop condition. |
| Can I inspect real evidence? | **PARTIAL / CURRENT BOTTLENECK** | On-page examples help, but the latest known site state still lacks a clean public jump to source artifacts/GitHub evidence. Public evidence links were intentionally hidden rather than filled with placeholders. That is truthful, but it interrupts the manager's verification path. |

### Reader B friction

| ID | Severity | Friction | Action |
|---|---:|---|---|
| B-01 | High | No single “inspect the proof” launch point. | Put one **Inspect Technical Proof** CTA at the top of Engineering Proof and route it to the compact proof strip/evidence index. |
| B-02 | High | The explanation can outrun the directly inspectable artifact trail. | Each major proof card should expose one concise receipt/snippet and, once real public URLs exist, one source link. |
| B-03 | Medium | Testing is described more easily than it is verified. | Lead with one real named result: test → observed defect or missing authority → minimum repair or truthful block → final result. CI-008 is especially useful because `BLOCKED_BY_MISSING_AUTHORITY` demonstrates non-fabrication. |

**Reader B target after fix:** architecture, quality, provenance, testing, and inspectable evidence all reachable in no more than three page transitions.

---

## Reader C — Engineer, 5–10 minutes

**Expected path:** Engineering Proof → evidence index → Constraint case study → Integrity/defect handling → GitHub/source evidence.

| Engineer lookup | Result | Current scan behavior |
|---|---|---|
| Schemas / contracts | **PARTIAL** | Contract concepts are visible, but an engineer should be able to land on an actual compact schema/contract excerpt without guessing. |
| Transformations | **PARTIAL** | The end-to-end case shows transformation stages, but source-level before/after structure needs a clearer inspectable target. |
| Tests | **PARTIAL** | Test-first behavior is visible; direct artifact-level inspection is still the weak hop. |
| Lineage / provenance | **PASS_CONCEPTUALLY / PARTIAL_INSPECTION** | The architecture and case make lineage understandable, but the evidence path should expose an actual receipt or linked lineage object. |
| Representative outputs | **PASS** | The constraint case provides an understandable representative output and correctly avoids presenting it as a live trading/market result. |
| Defect handling | **PASS** | Named failures, authority rejection, and the refusal to fabricate missing fields give the engineer a meaningful failure-handling story. |
| Runnable or inspectable technical material | **CURRENT FAIL** | No fake demo should be manufactured. Until the public GitHub/evidence route is connected, the engineer cannot complete the final verification hop from site narrative to source material. |

### Reader C friction

| ID | Severity | Friction | Action |
|---|---:|---|---|
| C-01 | High | The engineer must infer where schema, transformation, test, lineage, defect, and output evidence live. | Add an **Evidence Index** at the top of Engineering Proof with direct anchors: `SCHEMA` · `TRANSFORMATION` · `CONTRACT` · `LINEAGE` · `TEST` · `DEFECT` · `OUTPUT`. |
| C-02 | High | Public source inspection is not yet connected. | W4 GitHub front door should be the final hop. Do not expose the internal ZIP/version factory; route directly to selected public-safe artifacts. |
| C-03 | Medium | Evidence type can be misunderstood if labeling is separated from the artifact. | Keep `INTEGRATED`, `SYNTHETIC_SHADOW_ONLY`, or `REPRESENTATIVE` adjacent to every displayed proof item. |
| C-04 | Low | It is tempting to solve deep-scan friction by adding more pages. | Do not. Improve navigation and evidence density inside the existing proof surfaces. |

---

## Surgical fixes only

1. **Do not touch the frozen hero copy or approved badges.** Add the engineering-focus line below the hero, where proof begins.
2. **Use W2 as the universal fast path.** The proof strip should become the 30–90 second bridge from marketing-level comprehension to technical verification.
3. **Add one Evidence Index to Engineering Proof.** Seven anchors are enough: schema, transformation, contract, lineage, test, defect, output.
4. **Make one test lifecycle unmistakable.** Prefer real failure handling over a wall of green checks: observed defect or missing authority → bounded action → rerun or truthful block.
5. **Connect W4 GitHub only when the real URLs are ready.** Until then, keep links absent rather than shipping dead buttons or fake runnable claims.
6. **Keep evidence labels attached to evidence.** A representative constraint output must say `REPRESENTATIVE`; synthetic/shadow evidence must keep its label everywhere.
7. **No visual redesign.** Current layout, dark technical presentation, architecture visual, navigation, and spacing are already adequate for the scan goal. The remaining problem is proof routing, not cosmetics.

---

## Recommended scan path after W2/W4 merge

**Recruiter:**  
`HERO → CAPABILITIES → PROOF STRIP`

**Engineering manager:**  
`HERO → ARCHITECTURE → PROOF STRIP → ENGINEERING PROOF / INTEGRITY`

**Engineer:**  
`ENGINEERING PROOF → EVIDENCE INDEX → SELECTED ARTIFACT → GITHUB SOURCE`

This creates progressive disclosure instead of forcing every reader through the same depth.

---

## Re-test acceptance

| Check | Required result |
|---|---|
| Recruiter can state what HYDRA is | ≤ 10 seconds |
| Recruiter can identify engineering discipline and technical areas | ≤ 30 seconds |
| Manager can explain architecture, quality enforcement, provenance, and testing | ≤ 2 minutes |
| Manager can reach a real proof artifact | ≤ 3 page transitions |
| Engineer can find schema, transformation, test, lineage, output, and defect evidence | ≤ 2 clicks from Engineering Proof |
| Engineer can reach source/runnable-or-inspectable material | Yes, once W4 public GitHub path is connected |
| Dead/placeholder proof links | 0 |
| Unlabeled representative/synthetic proof | 0 |
| Site-wide redesign required | No |

---

## Final W6 verdict

`RECRUITER_SCAN_PATH_AUDIT=COMPLETE`

`READER_A=PASS_WITH_MINOR_FRICTION`

`READER_B=PASS_WITH_HIGH_VALUE_EVIDENCE_FRICTION`

`READER_C=PARTIAL_BLOCKED_AT_SOURCE_INSPECTION`

`PRIMARY_FRICTION=PROOF_DISCOVERABILITY_AND_PUBLIC_SOURCE_ACCESS`

`REDESIGN_REQUIRED=NO`

`SURGICAL_FIX_DIRECTION=W2_PROOF_STRIP + ENGINEERING_PROOF_EVIDENCE_INDEX + W4_GITHUB_HANDOFF`

The site already tells the right story. The next gain is not more story. It is making the receipts one click closer.
