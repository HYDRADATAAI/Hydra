# W6_PROOF_ROUTING_CLOSURE_CONTRACT

**Owner:** W2/W4 website integration lanes  
**Consumer:** W6 Recruiter Scan Test  
**Purpose:** Close the only high-value friction identified by W6 without redesigning the site.

## Current W6 state

`READER_A=PASS_WITH_MINOR_FRICTION`

`READER_B=PASS_WITH_HIGH_VALUE_EVIDENCE_FRICTION`

`READER_C=PARTIAL_BLOCKED_AT_SOURCE_INSPECTION`

`PRIMARY_FRICTION=PROOF_DISCOVERABILITY_AND_PUBLIC_SOURCE_ACCESS`

The website story is not the blocker. The final verification path is.

---

# REQUIRED CHANGE 1 — ONE FAST PROOF ENTRYPOINT

Add one obvious entrypoint at the beginning of the technical-proof area:

**Label:** `INSPECT TECHNICAL PROOF`

It must route to the recruiter proof strip from W2.

Do not add multiple competing proof CTAs.

The reader should move:

`HERO`
→ `TECHNICAL PROOF`
→ `EVIDENCE`

without deciding which of five buttons might contain the real engineering.

---

# REQUIRED CHANGE 2 — EVIDENCE INDEX

At the top of the Engineering Proof surface, expose exactly these categories:

`SCHEMA`
`TRANSFORMATION`
`CONTRACT`
`LINEAGE`
`TEST`
`DEFECT`
`OUTPUT`

Each category must resolve to an actual on-page artifact or a selected public-safe GitHub artifact.

No placeholder anchors.

No empty cards.

No “coming soon.”

If a category does not yet have public-safe evidence, omit the link rather than fabricating completion.

---

# REQUIRED CHANGE 3 — ONE COMPLETE ENGINEERING LIFECYCLE

W2 should make one compact lifecycle visible without opening giant logs.

Preferred lifecycle:

`INPUT / SOURCE`
↓
`NORMALIZE`
↓
`CONTRACT / AUTHORITY CHECK`
↓
`TRACE`
↓
`VALIDATE`
↓
`DEFECT OR BLOCK`
↓
`BOUNDED RESOLUTION`
↓
`FINAL STATE`

Use a genuine HYDRA example.

Strong public-safe candidates already identified by the project include:

### Cross-thread linkage example

`DEFECT-001 CROSS_THREAD_MACHINE_LINKAGE_ABSENT`

Then:

`minimum bounded repair`
→ `rerun`
→ `PASS_REPAIRED_CI_TEST_004`

This demonstrates defect discovery, bounded repair, rerun, baseline preservation, and release behavior.

### Authority/admissibility example

`CI-008`

Key principle:

**Discoverable data is not automatically authorized data.**

Permitted outcome:

`BLOCKED_BY_MISSING_AUTHORITY`

Important supporting behavior:

`SEMANTIC_VALUES_INVENTED=NO`

Do not rewrite a truthful blocked outcome into a fake green pipeline.

---

# REQUIRED CHANGE 4 — KEEP EVIDENCE TYPE ATTACHED

Every proof item must visibly retain its evidence state.

Use only applicable labels:

`INTEGRATED`
`SYNTHETIC`
`SHADOW`
`SYNTHETIC_SHADOW_ONLY`
`REPRESENTATIVE`

Do not put the label three sections away from the artifact.

The reader should never have to guess whether a displayed result is live production, integrated test evidence, synthetic/shadow evidence, or a representative presentation object.

---

# REQUIRED CHANGE 5 — W4 GITHUB HANDOFF

The GitHub front door becomes the final verification hop.

The website must not dump readers into repository archaeology.

The public path should land on the curated recruiter-facing README / proof area containing:

- architecture;
- data flow;
- engineering principles;
- selected technical proof;
- representative constraint example;
- testing evidence;
- real-vs-synthetic statement;
- repository map;
- safe runnable or inspectable path.

Do not lead with:

- hundreds of ZIP files;
- giant internal version trees;
- stale handoff packets;
- deprecated artifacts;
- internal factory naming without explanation.

If no safe runnable demo exists, provide an inspectable path instead.

Never manufacture a runnable demo to make W6 green.

---

# REQUIRED CHANGE 6 — ENGINEERING FOCUS LINE

Outside the frozen hero, add one compact orientation line near the first technical section:

> Engineering focus: data ingestion, contract validation, provenance and lineage, integration testing, and market constraint intelligence.

Purpose:

The recruiter should not need to infer the engineering discipline solely from architecture vocabulary.

Do **not** turn this into a biography block.

Do **not** modify the frozen hero.

---

# DO NOT CHANGE

Keep the approved hero foundation:

`HYDRA / MARKET INTELLIGENCE DATA PLATFORM`

`Turn fragmented market data into traceable intelligence.`

Approved capability badges remain:

`Multi-source ingestion`

`Contract-bound handoffs`

`Lineage + release gates`

Do not re-add:

`AWS CLOUD · NEXT`

`GEN AI · EMERGING`

`AI FUTURE`

`SIMULATED FLOW`

`Independent engineering project`

No decorative redesign binge.

No new architecture.

No new HYDRA execution is authorized by this packet.

---

# W6 RETEST CONTRACT

When W2/W4 return a merged public build, rerun W6 from zero.

## Reader A — 30 seconds

Must answer:

- What is HYDRA?
- What engineering discipline does it demonstrate?
- What technical areas are visible?

Required state:

`READER_A=PASS`

## Reader B — 2 minutes

Must answer:

- architecture;
- quality enforcement;
- provenance;
- testing;
- where to inspect evidence.

Required state:

`READER_B=PASS`

A real technical proof item must be reachable in no more than **3 page transitions**.

## Reader C — 5–10 minutes

Must locate:

- schema/contract;
- transformation;
- lineage;
- test;
- defect handling;
- representative output;
- public-safe source or inspectable material.

Required state:

`READER_C=PASS`

Technical evidence categories should be reachable in no more than **2 clicks from Engineering Proof**.

---

# STOP CONDITION

This W6 lane is now parked.

Do not create additional W6 website features.

Resume only when a merged build containing W2 proof routing and W4 GitHub/public evidence routing is available.

Then:

`RERUN W6`
→ if green, authorize `W7`
→ if not green, repair only the observed friction.

---

# STATUS

`W6_PROOF_ROUTING_CLOSURE_CONTRACT=ISSUED`

`W6_EXECUTION_STATE=PARKED_PENDING_W2_W4_MERGE`

`NEW_ARCHITECTURE_AUTHORIZED=NO`

`HERO_REDESIGN_AUTHORIZED=NO`

`HYDRA_CORE_EXECUTION_AUTHORIZED=NO`

`NEXT_EVENT=MERGED_PUBLIC_BUILD_RETURNED_FOR_W6_RETEST`
