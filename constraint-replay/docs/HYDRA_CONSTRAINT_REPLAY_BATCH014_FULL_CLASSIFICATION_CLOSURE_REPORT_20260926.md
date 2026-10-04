# HYDRA Constraint — Classified Gold Closure
## Batch 014 — 2026-09-26

Status: **22 / 22 REPLAY-READY CASES CLASSIFIED · 0 CALIBRATED**

Batch 014 closes governed historical classification coverage across the entire Batch 005 replay-ready corpus.

It does **not** close probabilistic calibration.

## Final four cases

### Nord Stream 2 certification state

Historical mechanism source:
- Bundesnetzagentur, 16 November 2021.
- Certification would remain suspended until specified German-law organizational and documentation conditions were satisfied.

Outcome:
- German Federal Ministry for Economic Affairs and Climate Action, 22 February 2022.
- The prior Security of Supply Report was withdrawn and the certification procedure was halted pending reassessment; a favourable certification decision could not be issued while the report remained withdrawn.

Governed class:
`PARTIAL_REALIZATION`

Reason:
The certification-block mechanism persisted in the expected direction, but the later halt rested on a different security-of-supply/geopolitical reassessment rather than only the organizational conditions identified in November 2021.

Confidence:
`NO_ADMISSIBLE_NUMERIC_CONFIDENCE`

### Japan–Korea export-control relations

Historical mechanism source:
- WTO DSB record, 29 July 2020.
- Korea described the licensing requirements as seriously restricting exports and creating delays, uncertainty and costs.
- Japan maintained that the measures were consistent with ordinary international export-control practices.

Outcome:
- Korean MOTIE, 16 March 2023: described Japan as suspending the three-item export regulations and announced Korea's WTO-complaint withdrawal.
- Japanese METI, 17 March 2023: stated that the measures should not be understood as having been lifted and that Korea's former white-list status had not yet been restored.

Governed class:
`UNEVALUABLE`

Reason:
The normalization process is documented, but the two governments preserved materially different characterizations of the legal/regulatory state.

HYDRA does not choose one government's characterization as uncontested fact.

### Eastern Mediterranean offshore-drilling dispute

Historical mechanism source:
- U.S. Congressional Research Service, 1 April 2019.
- CRS described competing offshore hydrocarbon claims and drilling-related naval activity as raising tensions and negatively affecting settlement negotiations, while commercial gas development remained uncertain.

Outcome:
- Council of the European Union, 9 November 2023.
- The drilling-related restrictive-measures framework was renewed, two individuals remained listed, and the EU retained the ability to impose further targeted measures.

Governed class:
`UNEVALUABLE`

Reason:
The sanctions/tension mechanism persisted, but competing maritime, sovereignty and hydrocarbon-rights claims remained unresolved and the later sanctions renewal does not itself adjudicate those claims or establish a clean economic outcome.

### EU CBAM transitional phase

Historical mechanism source:
- UNCTAD, 14 July 2021.
- UNCTAD modelled CBAM as shifting trade toward more carbon-efficient production, reducing some developing-country exports and only modestly lowering global emissions.

Operational outcome:
- European Commission DG TAXUD, 14 January 2026.
- definitive CBAM regime successfully deployed from 1 January 2026;
- >12,000 authorisation applications by 7 January;
- >4,100 authorised declarants;
- 10,483 validated CBAM customs declarations;
- 1,655,613 tonnes of goods covered by declarations in the first 1–6 January window.

Governed class:
`UNEVALUABLE`

Reason:
Administrative/operational implementation is measurable, but those January 2026 figures do not resolve UNCTAD's medium-term modeled trade-reallocation, developing-country export and global-emissions effects.

The economic outcome window is therefore treated as incomplete.

## Corpus closure

Batch 005 replay-ready corpus:
- 22 sourced historical case families;
- 82 historical replay cuts;
- 31 executable policy events;
- 9 original later observations.

Batch 014 classified corpus:
- **22 classified historical cases**
- **0 calibrated historical cases**

Outcome distribution:
- **17 `PARTIAL_REALIZATION`**
- **5 `UNEVALUABLE`**

No replay-ready case remains without governed classification.

## Evidence-availability lead time

For the final four:

- Nord Stream 2: 98 days
- Japan–Korea: 960 days
- Eastern Mediterranean: approximately 1,682.74 days
- CBAM: 1,645 days

Across all 22 classified cases:

- mean first admitted outcome-evidence lead time: approximately **735.22 days**
- median: approximately **450.14 days**

These are source-availability intervals.

They are **not**:
- first effect onset;
- trading lead time;
- profitability windows;
- causal-lag estimates.

Several cases rely on later retrospective studies or on eventual legal/operational records.

## Closure invariants

Batch 014 regression requires:

- the classified case set to exactly equal the immutable replay-ready case set;
- all 18 Batch 013 predecessor records to remain unchanged;
- the final four cases to already exist in replay-ready history;
- hypothesis/outcome publishers to remain distinct;
- hypothesis evidence to predate admitted outcomes;
- no numeric confidence admission;
- mapping evidence to equal admitted enrichment evidence;
- Nord Stream 2 to map `PARTIAL_REALIZATION`;
- Japan–Korea to preserve an open contradiction and map `UNEVALUABLE`;
- Eastern Mediterranean to preserve unresolved dispute status and map `UNEVALUABLE`;
- CBAM to preserve an incomplete modeled economic-outcome window and map `UNEVALUABLE`;
- governing Git blob pins to match checked-out bytes;
- all 22 promotion decisions to have zero classification blockers;
- all 22 to remain calibration-blocked;
- Brier score to remain disabled.

## What is complete

The current 22-case corpus now supports governed historical answers to:

- what information was knowable at a replay cut;
- what mechanism was hypothesized;
- what later outcome evidence became available;
- whether the historical case can be classified;
- whether contradictions or open horizons prevent classification;
- how long until the first admitted outcome evidence appeared.

## What is not complete

The corpus is **not probabilistically calibrated**.

No current case has admissible historical numeric confidence provenance under the existing standard.

Therefore:

- calibrated/scored gold count remains 0;
- Brier score remains unavailable;
- probability calibration remains a separate evidence-acquisition problem.

This is an acceptable terminal state for historical cases where authentic probability provenance does not exist.

## Next material step

Do not continue creating classification batches merely for activity.

The classification coverage objective is now complete.

The next serious work should move to one of these distinct goals:

1. locate authentic historical probability/confidence provenance for a subset of the 22 cases;
2. build aggregate evaluation/reporting across the 22 classified cases;
3. integrate the classified replay corpus into the authoritative central Constraint runtime/query path;
4. execute the first serious end-to-end Constraint replay run using the current governed evidence stack.

Classification itself should now stop unless new historical cases are deliberately added.
