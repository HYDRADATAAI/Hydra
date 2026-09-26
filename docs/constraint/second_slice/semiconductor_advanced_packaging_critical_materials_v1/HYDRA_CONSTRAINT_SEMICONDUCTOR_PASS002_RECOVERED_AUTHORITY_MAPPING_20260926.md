# HYDRA Constraint semiconductor — Pass 002 authority recovery and mapping

Result: **Thread-3 contract-content blocker cleared on this branch. Semiconductor runtime admission remains BLOCKED.**

This is a successor to Pass 001, not a rewrite of it. The exact requested master ZIP was recovered and its SHA-256 matches `ab7e4c05c9210a90256b8cdea89eeb9f3bb551453dfe13ebfe44616f750cb366`. The original archive bytes are preserved under `docs/constraint/authority/thread3_recovered_pass002_20260926/`. Original internal names are retained to preserve the historical archive hash. Readable copies carry this pass's unique prefix; their index records original members and hashes.

## Authority and runtime ownership

Batch 7 supplies the consolidated contract, Batch 8 supplies cross-thread ownership clarification, and Batch 9 supplies the conformance campaign. Earlier batches remain available inside the unchanged master ZIP. Batch 7 section 155 preserves more-specific earlier rules unless explicitly replaced; these mappings are not a substitute for those rules.

Thread-3 is a semantic workstream, not Pipeline T3. Batch 8 Decisions 304–305 bind candidate occurrence formation to `PIPELINE_T5_CONSTRAINT_FORMATION`, and canonical governance plus beneficiary relationships to T6. Thread-2 mechanism classes and Trust Governance provenance/independence policies remain external inputs. No new mechanism registry, identity namespace, provenance model, or graph is introduced here.

## Semiconductor mapping to recovered rules

These are implementation requirements, not populated facts or admitted records. B7 means the recovered Batch-7 contract; B8 means the recovered Batch-8 delta. Campaign cases name existing Batch-9 tests, not newly passed tests.

| Semiconductor requirement | Recovered authority | Existing representation / remaining implementation gap | Existing campaign case |
|---|---|---|---|
| Same facility, distinct packaging / HBM limiting mechanisms | B7 §§5, 36, 150; B8 Decisions 311–312 | Physical `Node.node_id` identifies a graph node. It does not prove T6 mechanism-based canonical identity. Consume owner resolution. | T3-ID-004 |
| Candidate occurrence versus canonical constraint | B8 Decisions 304–305 | T5 candidate IDs must remain semantically separate from T6 `constraint_id`. | T3-XAUTH-005; full owner boundary campaign still needed |
| Nameplate versus usable capacity | B7 §§31, 80, 115, 146, 150 | Physical `Snapshot.capacity_nameplate`, `capacity_usable`, and `capacity_unit` are reusable structural fields. They do not prove capturable allocation. | T3-BEN-003; T3-NULL-001 |
| Planned, committed, reserved, and qualified capacity | B7 §§16, 80, 117, 146 | No verified complete allocation/qualification transport mapping. Generic attributes are not proof of owner conformance. | T3-CAP-004; T3-BLOCK-005 |
| Multiple products sharing one packaging line | B7 §§80, 146, 150 | Facility/capability allocation must prevent double counting across product and beneficiary relationships. | T3-CAP-002; T3-CAP-003 |
| Qualification failure or own material shortage | B7 §§16, 115–116 | Preserve explicit capture blockers and re-adjudicate; physical capacity alone cannot grant beneficiary authority. | T3-BLOCK-001; T3-BLOCK-004 |
| Facility operator, parent, JV and offtake rights | B7 §§17, 81–82, 118 | Country/company nodes do not establish economic attribution. Use governed ownership and rights history. | T3-ENTITY-004; T3-CORP-001 |
| Supplier association versus economic capture | B7 §§14, 19, 22–28 | Physical beneficiary nodes/relations are structural. T6 requires supported capability, enabler, exposure and capture links. | T3-BEN-002; T3-BEN-006 |
| Power / water / material dependency cycles | B7 §§74–77, 110–112 | Type causal dependencies separately from evidentiary support; causal cycles must not self-corroborate. | T3-DAG-002; T3-DAG-004 |
| Syndicated supplier reports | B7 §§8, 26, 83, 150; B8 Decision 321 | `Provenance` source fields are not a substitute for owner independence groups and ultimate-origin lineage. | T3-EVID-001 |
| Contradiction or scope change | B7 §§6, 40, 150; B8 Decisions 317–321 | Candidate conflict summaries consume, rather than replace, evidence contradiction and quality policy. | T3-CONFLICT-002; T3-CONFLICT-004 |
| Acquisition, capacity ramp and revised historical knowledge | B7 §§7, 18, 117–118, 127–130 | Physical `known_at` dates do not establish complete `available_at`, `decision_at` and policy-version semantics. | T3-TIME-003; T3-TIME-005 |
| Bottleneck migration, merge or split | B7 §§39–48, 119–120 | Explicit lineage, evidence allocation and recomputation required. Do not clone confidence or beneficiaries. | T3-SPLIT-002; T3-SPLIT-003 |
| Yield and detailed qualification dimensions | B7 §§35–38; B8 Decisions 310–316 | The recovered contract governs handling and promotion, but does not establish the slice's detailed yield/qualification transport fields. Exact owner schema mapping remains unresolved. | T3-XAUTH-001; T3-NULL-005 |

## Inspected implementation pins

- Physical structure: `constraint/physical-dependency-graph-v1` at `cc53a77bec31a17800f7f431a7cd83771864edd2`, file `constraint-physical-dependency/src/hydra_constraint_physical/models.py`.
- Owner-seam branch: `constraint/lily-owner-seam-reconciliation-v1-20260926` at `b79a8533a94d8101e213e5971066f8518cf3742d`. Its standalone validator at `tools/validate_constraint_lily_owner_seams.py` was inspected. It explicitly prints `CANONICAL_IDENTITY_STATE=NOT_EVALUATED`, `RAW_LINEAGE=BLOCKED_INCOMPLETE_T1_T2`, and `STRICT_ACCEPTANCE=BLOCKED`; its existence is not runtime admission evidence. It was not executed in this pass.

These pins record discovery, not branch selection or mainline admission. Concurrent branch movement must be reconciled against exact commits before integration.

## Verification and successor state

Run from the repository root:

```bash
python3 tools/verify_hydra_constraint_semiconductor_pass002_thread3_authority_20260926.py
```

The verifier checks the pinned master hash, every listed outer and nested member's size/digest, and byte equality of the readable authority copies. It does not execute the Batch-9 semantic campaign or validate semiconductor replay. Runtime assertions remain unpromoted.

Cleared: `OWNER_CONTRACT_CONTENT_UNAVAILABLE` for Thread-3 on this branch.

Remaining: native identity/provenance owner integration; first-slice strict acceptance; physical/policy/replay branch admission; semiconductor evidence population; exact yield/qualification/capacity schema mapping; ordinary historical replay/evaluation. No facilities, suppliers, materials, canonical constraints, or qualified beneficiaries were populated by this pass.

Next executable step: bind the recovered B7/B8/B9 authority to the actual T6 identity and provenance implementation, reconcile its exact implementation commit with the physical/policy/replay owner path, and run the relevant owner campaign. Do not request the Thread-3 ZIP again: it is now preserved in this repository branch. Missing runtime owners remain an implementation discovery/integration task, not a reason to reopen the closed semantic contract.
