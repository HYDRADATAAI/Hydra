# HYDRA Constraint semiconductor Pass004 — first reviewed source seed

Base: `07e03eeede02e77c3076a75aef274f3f8b424158`. Predecessor scope: Thread-6 Batch017. Earlier owner-lineage repair remains independently reviewable in PR #88; its six observed CI workflows passed at head `3dc29ceeabc3c43caf3620c23c1234221f868340`.

## Added records

- 4 registered primary-source releases.
- 8 manually reviewed evidence observations.
- 15 scoped field updates using Batch017 field names.
- 0 canonical entities, facilities, constraints or qualified beneficiaries minted.
- 0 of the 14 required semiconductor replay cases executed.

The source registry covers the 2024 SK hynix Indiana announcement, Micron HBM3E production/sampling release, TSMC Arizona expansion release, and Amkor–TSMC packaging MOU. URLs, publication dates and paragraph locators are embedded in each source record. These are issuer statements, not independent corroboration. A joint announcement is registered once; its two named publishers do not create two independent sources.

The seed addresses HBM and advanced packaging, plus a narrow fab/water-design observation. It does not complete Batch017's bounded universe or establish equipment/material bottlenecks, quantitative spare capacity, qualification completion, usable output, captured economic value, or observed project outcomes.

## Reuse and identity boundary

This pass reuses the existing first-slice source-registry-extension, evidence-seed and field-population-overlay transport shapes. Each document names the predecessor artifact it follows and supplies the semiconductor `slice_id`. The inherited schema-version labels deliberately retain their existing first-slice names: these are seed document formats, not a newly introduced runtime contract.

Field names come directly from the 60-field Batch017 envelope. Scope strings identify what the source discusses for manual review; they are not canonical entity or facility identifiers. The staged SRC/EV references join these seed documents only. Owner-issued entity, facility, geography, supplier and source-version identities remain unresolved. No second identity service, provenance engine, graph, event model or runtime adapter was created.

## Time and evidence limits

Publication dates describe the releases. The conservative `available_at` and manual-review `acquired_at` timestamps are `2026-09-26T21:10:37Z`, after the selected source passages were inspected in this session. The availability basis explicitly identifies web-extract review completion, not acquisition of raw HTTP response bytes. No 2024 knowledge-as-of eligibility is claimed.

The observations describe announcement-era statements, not present operating status. Future capacity plans remain plans. Product volume production does not establish facility throughput or unused capacity. Sampling plans do not establish completed sampling. Water design goals do not establish delivered water or achieved recycling. Planned packaging technologies do not establish qualified site capability.

Raw source bodies were not persisted through T1. Accordingly `source_content_persisted`, raw-lineage eligibility and strict-original-as-of readiness remain false; source-version and raw-artifact digest slots remain null. Effective operational intervals are unknown. Unknown quantitative capacity, yield, qualification-completion and confidence fields stay unresolved.

## Verification and CI

Executed successfully:

```bash
python tools/validate_constraint_semiconductor_pass004_source_seed.py
python tools/test_constraint_semiconductor_pass004_source_seed.py
python tools/validate_constraint_second_slice_batch017_audit.py
python tools/test_constraint_second_slice_batch017_audit_adversarial.py
```

Pass004 tests include a positive baseline and 14 negative mutations. They reject unknown/duplicate references, fabricated raw custody/source versions, backdated source/observation/field availability, invented operational dates, unknown capacity converted to zero, foreign fields, missing unresolved-identity boundaries, fake admission and fake replay execution. These are seed-integrity tests, not execution of the 14 domain replay cases. The ten historical Batch017 hostile checks also pass unchanged.

The existing second-slice workflow now runs the new seed checker and mutation tests. Historical Batch017 audit/status/master files remain unchanged. Their original no-population statement remains the historical audit result; this report records the subsequent small reviewed seed without declaring the domain fully populated.

## Next executable work

Materialize the registered releases through the existing T1 acquisition path and bind the resulting source versions to the existing T2/T3/T4 provenance and identity owners. Expand evidence coverage into equipment and critical-material dependencies within Batch017 scope. Execute semiconductor cases only once the relevant owner integration and evidence boundaries are satisfied. Strict replay, ordinary T6 admission and the first semiconductor run remain BLOCKED.
