# PASS W1 — PUBLIC PROOF INVENTORY + CLAIM AUTHORITY MAP

**Deliverable:** `PUBLIC_PROOF_INVENTORY_CLAIM_AUTHORITY_MAP`

**Disposition:** `MATERIALLY_GREEN_WITH_EXPLICIT_HOLDS`

**Rule:** A missing receipt does not become a marketing sentence.

## Executive result

- Candidate claims inventoried: **15**
- Public-safe now: **11**
- Held from public use pending stronger evidence: **4**
- Unsupported claims authorized for publication: **0**
- Synthetic/shadow evidence is labeled rather than presented as live/production proof.
- CI-008 blocker evidence is treated as positive governance proof, not hidden as a failure.

## Public-safe claim set

- **W1-C001** — HYDRA has an integrated governed seam spanning T1 through T5.  
  Evidence: `CI_TEST_004_REPAIRED_RERUN_RESULT_V004.json`  
  Label: `INTEGRATED / SYNTHETIC_SHADOW`
- **W1-C002** — HYDRA verifies reverse references and preserves a pinned baseline during integrated seam testing.  
  Evidence: `CI_TEST_004_REPAIRED_RERUN_RESULT_V004.json`  
  Label: `INTEGRATED / SYNTHETIC_SHADOW`
- **W1-C003** — HYDRA has behavioral seam tests for replay, lineage, reverse trace, fault localization, and release blocking across T3–T5.  
  Evidence: `BEHAVIORAL_SEAM_RECEIPT.json`  
  Label: `INTEGRATED / CONTROLLED_REBASELINE`
- **W1-C004** — HYDRA can quarantine a governed case and block its release downstream.  
  Evidence: `CI_TEST_006_REPAIRED_RERUN_SUMMARY_V002.txt`  
  Label: `INTEGRATED / SYNTHETIC_SHADOW`
- **W1-C005** — HYDRA uses defect-scoped minimum repair followed by rerun rather than broad speculative rewrites.  
  Evidence: `CI_TEST_006_REPAIRED_RERUN_SUMMARY_V002.txt`  
  Label: `INTEGRATED / SYNTHETIC_SHADOW`
- **W1-C006** — HYDRA checks deterministic replay across independent processes.  
  Evidence: `CI_TEST_007_SUMMARY_V001.txt`  
  Label: `INTEGRATED / SYNTHETIC_SHADOW`
- **W1-C007** — HYDRA refuses to fabricate missing T5→T6 admissibility authority.  
  Evidence: `CI_TEST_008_V012_RESULT.json`  
  Label: `INTEGRATED / AUTHORITY-GATED / SYNTHETIC_SHADOW`
- **W1-C008** — When required native fields are absent, HYDRA preserves the blocker instead of inventing semantic values.  
  Evidence: `CI_TEST_008_V011_RESULT.json`  
  Label: `INTEGRATED / AUTHORITY-GATED`
- **W1-C009** — The retrieved integrated-test evidence is explicitly not production/live ML evidence.  
  Evidence: `CI_TEST_004_REPAIRED_RERUN_RESULT_V004.json; CI_TEST_007_SUMMARY_V001.txt; CI_TEST_008_RESULT_V001.json`  
  Label: `SYNTHETIC / SHADOW`
- **W1-C014** — HYDRA preserves lineage/history and reverse trace through tested downstream seams.  
  Evidence: `BEHAVIORAL_SEAM_RECEIPT.json; CI_TEST_007_SUMMARY_V001.txt`  
  Label: `INTEGRATED / CONTROLLED / SYNTHETIC_SHADOW`
- **W1-C015** — HYDRA uses contract/release-gate behavior that can block unresolved data.  
  Evidence: `BEHAVIORAL_SEAM_RECEIPT.json; CI_TEST_006_REPAIRED_RERUN_SUMMARY_V002.txt`  
  Label: `INTEGRATED / SYNTHETIC_SHADOW`

## Hold / do-not-publish set

- **W1-C010** — HYDRA has canonical-identity safety rules for Constraint classification.  
  Status: `VERIFIED_WITH_LABEL`  
  Reason: Specifications require classifier cannot mint canonical identity, cannot fabricate Constraint existence, and must preserve ambiguity/provenance. Execution receipt was not recovered in this W1 evidence pull.
- **W1-C011** — N1 semantic classification passed 38/38 tests.  
  Status: `AMBIGUOUS`  
  Reason: Current W1 retrieval found N1 specifications but not the final machine receipt that directly substantiates 38/38.
- **W1-C012** — HYDRA performs multi-source ingestion.  
  Status: `AMBIGUOUS`  
  Reason: Integrated downstream seam evidence exists, but this W1 pull did not recover a clean execution receipt proving the public-facing multi-source ingestion claim.
- **W1-C013** — HYDRA normalizes fragmented source data into controlled internal records.  
  Status: `AMBIGUOUS`  
  Reason: Architecture/specification references normalization, but direct recruiter-safe transformation evidence was not recovered here.

## Recruiter-safe strongest proof path

1. **Integrated path:** T1 → T2 → T3 → T4 → T5 is exercised in CI-TEST-004.
2. **Trace:** reverse references, lineage digest, why-trace, and reverse trace are checked.
3. **Validate:** behavioral seam and release-gate checks pass under controlled/synthetic-shadow boundaries.
4. **Defect:** the quarantine case is deliberately driven into a governed failure path.
5. **Minimum repair:** a defect-scoped overlay repairs the demonstrated defect without mutating the pinned baseline.
6. **Rerun:** deterministic replay reproduces byte-identical outputs.
7. **Authority refusal:** CI-008 remains blocked when required native authority is missing, with `semantic_values_invented=false`.

## Claim guardrails for W2–W6

- Keep `SYNTHETIC_SHADOW_ONLY`, controlled-rebaseline, or representative labels wherever the evidence requires them.
- Do not claim production deployment, live execution, live classification accuracy, Baby ML training, Serious ML training, or canonical promotion from these receipts.
- Do not publish `N1 = 38/38 PASS` until the final execution/seal receipt is recovered into the evidence set.
- Do not strengthen `Multi-source ingestion` or normalization wording until W2/W5 can bind those claims to direct artifacts.
- Prefer the phrase **blocked rather than fabricated** for CI-008, because the receipts explicitly support it.

## Detailed claim map

### W1-C001
- **PUBLIC_CLAIM:** HYDRA has an integrated governed seam spanning T1 through T5.
- **SOURCE_ARTIFACT:** CI_TEST_004_REPAIRED_RERUN_RESULT_V004.json
- **SOURCE_LOCATION:** HYDRA CI-TEST-004 repaired rerun receipt (retrieved evidence library)
- **EXACT_PROOF:** overall=PASS_REPAIRED_CI_TEST_004; observed buckets THREAD1_CONTRACTS → THREAD2_ADVERSARIAL → THREAD3_GOLDEN → THREAD4_LINEAGE → THREAD5_RELEASE_GATE; failure_count=0
- **EVIDENCE_CLASS:** INTEGRATED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Recruiter Proof Strip / Contract + Trace + Validate
- **GITHUB_DESTINATION:** README / Testing / Technical Proof
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C002
- **PUBLIC_CLAIM:** HYDRA verifies reverse references and preserves a pinned baseline during integrated seam testing.
- **SOURCE_ARTIFACT:** CI_TEST_004_REPAIRED_RERUN_RESULT_V004.json
- **SOURCE_LOCATION:** HYDRA CI-TEST-004 repaired rerun receipt
- **EXACT_PROOF:** REVERSE_REFERENCE_VERIFICATION=PASS; BATCH60_IMMUTABILITY_PIN=PASS; CANONICAL_BASELINE_MUTATED=NO
- **EVIDENCE_CLASS:** INTEGRATED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Trace / Lineage card
- **GITHUB_DESTINATION:** Testing / Integrity invariants
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C003
- **PUBLIC_CLAIM:** HYDRA has behavioral seam tests for replay, lineage, reverse trace, fault localization, and release blocking across T3–T5.
- **SOURCE_ARTIFACT:** BEHAVIORAL_SEAM_RECEIPT.json
- **SOURCE_LOCATION:** CI_TEST_005_FIRST_BEHAVIORAL_CROSS_THREAD_SEAM result
- **EXACT_PROOF:** T3_EXACT_REPLAY_MATCH=true; T3_LINEAGE_DIGEST_STABLE=true; T4_REVERSE_TRACE_COMPLETE=true; T4_WHY_TRACE_COMPLETE=true; T5_BLOCKER_IF_UNRESOLVED=true; failures=[]
- **EVIDENCE_CLASS:** INTEGRATED / CONTROLLED_REBASELINE
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Recruiter Proof Strip / Trace + Validate
- **GITHUB_DESTINATION:** README / Behavioral seam testing
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C004
- **PUBLIC_CLAIM:** HYDRA can quarantine a governed case and block its release downstream.
- **SOURCE_ARTIFACT:** CI_TEST_006_REPAIRED_RERUN_SUMMARY_V002.txt
- **SOURCE_LOCATION:** HYDRA CI-TEST-006 repaired rerun receipt
- **EXACT_PROOF:** OVERALL=PASS_REPAIRED_CI_TEST_006; T2_TO_T4_QUARANTINE_PATH=PASS; T4_TO_T5_RELEASE_BLOCK_PATH=PASS; EXACT_TARGET_INTEGRATED_QUARANTINE_DISPOSITION_PROVEN=PASS
- **EVIDENCE_CLASS:** INTEGRATED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Defect / Release Gate card
- **GITHUB_DESTINATION:** Testing / Quarantine + release gate
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C005
- **PUBLIC_CLAIM:** HYDRA uses defect-scoped minimum repair followed by rerun rather than broad speculative rewrites.
- **SOURCE_ARTIFACT:** CI_TEST_006_REPAIRED_RERUN_SUMMARY_V002.txt
- **SOURCE_LOCATION:** HYDRA CI-TEST-006 repaired rerun receipt
- **EXACT_PROOF:** AUTHORITY_MODE=DEFECT_SCOPED_REPAIR_OVERLAY; FAILURE_COUNT=0; V110_MODIFIED=NO; BATCH60_IMMUTABILITY_PIN=PASS
- **EVIDENCE_CLASS:** INTEGRATED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Defect → Resolution card
- **GITHUB_DESTINATION:** Engineering principles / Minimum repair
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C006
- **PUBLIC_CLAIM:** HYDRA checks deterministic replay across independent processes.
- **SOURCE_ARTIFACT:** CI_TEST_007_SUMMARY_V001.txt
- **SOURCE_LOCATION:** HYDRA CI-TEST-007 repaired quarantine replay receipt
- **EXACT_PROOF:** OVERALL=PASS_REPAIRED_QUARANTINE_REPLAY_DETERMINISM; CROSS_PROCESS_REPLAY_A_B_BYTE_IDENTICAL=PASS; REPLAY_A_EXACT_STORED_OVERLAY_MATCH=PASS; REPLAY_B_EXACT_STORED_OVERLAY_MATCH=PASS
- **EVIDENCE_CLASS:** INTEGRATED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Validate / Determinism receipt
- **GITHUB_DESTINATION:** Testing / Deterministic replay
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C007
- **PUBLIC_CLAIM:** HYDRA refuses to fabricate missing T5→T6 admissibility authority.
- **SOURCE_ARTIFACT:** CI_TEST_008_V012_RESULT.json
- **SOURCE_LOCATION:** HYDRA CI-TEST-008 V012 authority scan result
- **EXACT_PROOF:** overall=BLOCKED_V012_NO_COMPLETE_PER_FIELD_AUTHORITY_SET; authority_hit_count=0; complete_case_count=0; semantic_values_invented=false; batch60_immutability_pin=true
- **EVIDENCE_CLASS:** INTEGRATED / AUTHORITY-GATED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** YES
- **WEBSITE_DESTINATION:** Authority / Blocked-not-fabricated proof card
- **GITHUB_DESTINATION:** Engineering principles / Explicit authority
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C008
- **PUBLIC_CLAIM:** When required native fields are absent, HYDRA preserves the blocker instead of inventing semantic values.
- **SOURCE_ARTIFACT:** CI_TEST_008_V011_RESULT.json
- **SOURCE_LOCATION:** HYDRA CI-TEST-008 V011 result
- **EXACT_PROOF:** overall=BLOCKED_V011_EXACT_AUTHORITATIVE_CASE_SOURCE_REQUIRED; required_fields=[object_type, subject_entity_id, as_of, confidence, evidence_ids]; semantic_values_invented=false
- **EVIDENCE_CLASS:** INTEGRATED / AUTHORITY-GATED
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Contract / Authority rejection
- **GITHUB_DESTINATION:** Data contracts / Fail-closed behavior
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C009
- **PUBLIC_CLAIM:** The retrieved integrated-test evidence is explicitly not production/live ML evidence.
- **SOURCE_ARTIFACT:** CI_TEST_004_REPAIRED_RERUN_RESULT_V004.json; CI_TEST_007_SUMMARY_V001.txt; CI_TEST_008_RESULT_V001.json
- **SOURCE_LOCATION:** Integrated test receipts
- **EXACT_PROOF:** BOUNDARY=SYNTHETIC_SHADOW_ONLY; LIVE_HYDRA_DATA_USED=NONE where reported; CANONICAL_PROMOTION=NONE; BABY_ML_TRAINING=NONE; SERIOUS_ML=FROZEN
- **EVIDENCE_CLASS:** SYNTHETIC / SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Real vs Synthetic disclosure
- **GITHUB_DESTINATION:** README / Real vs synthetic
- **STATUS:** VERIFIED

### W1-C010
- **PUBLIC_CLAIM:** HYDRA has canonical-identity safety rules for Constraint classification.
- **SOURCE_ARTIFACT:** N1 work-unit contract / assignment artifacts
- **SOURCE_LOCATION:** Retrieved N1 specification artifacts
- **EXACT_PROOF:** Specifications require classifier cannot mint canonical identity, cannot fabricate Constraint existence, and must preserve ambiguity/provenance. Execution receipt was not recovered in this W1 evidence pull.
- **EVIDENCE_CLASS:** CONTRACT / DESIGN REQUIREMENT
- **PUBLIC_SAFE:** NO
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** HOLD until execution receipt is recovered
- **GITHUB_DESTINATION:** May document as design invariant only, clearly labeled
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C011
- **PUBLIC_CLAIM:** N1 semantic classification passed 38/38 tests.
- **SOURCE_ARTIFACT:** N1 V025 corrected post-repair seal reproof receipt (operator-known, not recovered in W1 search)
- **SOURCE_LOCATION:** Expected authoritative root D:\HYDRA / N1 closeout chain
- **EXACT_PROOF:** Current W1 retrieval found N1 specifications but not the final machine receipt that directly substantiates 38/38.
- **EVIDENCE_CLASS:** UNRECOVERED EXECUTION RECEIPT
- **PUBLIC_SAFE:** NO
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** DO NOT PUBLISH until receipt is recovered
- **GITHUB_DESTINATION:** DO NOT PUBLISH until receipt is recovered
- **STATUS:** AMBIGUOUS

### W1-C012
- **PUBLIC_CLAIM:** HYDRA performs multi-source ingestion.
- **SOURCE_ARTIFACT:** No direct public-safe execution receipt recovered in this W1 pull
- **SOURCE_LOCATION:** Evidence gap
- **EXACT_PROOF:** Integrated downstream seam evidence exists, but this W1 pull did not recover a clean execution receipt proving the public-facing multi-source ingestion claim.
- **EVIDENCE_CLASS:** UNPROVEN IN CURRENT W1 INVENTORY
- **PUBLIC_SAFE:** NO
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** HOLD current hero wording for W5 claim audit; do not strengthen
- **GITHUB_DESTINATION:** Do not claim runtime multi-source ingestion without source receipt
- **STATUS:** AMBIGUOUS

### W1-C013
- **PUBLIC_CLAIM:** HYDRA normalizes fragmented source data into controlled internal records.
- **SOURCE_ARTIFACT:** No direct normalization execution receipt recovered in this W1 pull
- **SOURCE_LOCATION:** Evidence gap
- **EXACT_PROOF:** Architecture/specification references normalization, but direct recruiter-safe transformation evidence was not recovered here.
- **EVIDENCE_CLASS:** UNPROVEN IN CURRENT W1 INVENTORY
- **PUBLIC_SAFE:** NO
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Use representative example only if W2 can bind it to genuine evidence
- **GITHUB_DESTINATION:** Hold execution claim pending artifact
- **STATUS:** AMBIGUOUS

### W1-C014
- **PUBLIC_CLAIM:** HYDRA preserves lineage/history and reverse trace through tested downstream seams.
- **SOURCE_ARTIFACT:** BEHAVIORAL_SEAM_RECEIPT.json; CI_TEST_007_SUMMARY_V001.txt
- **SOURCE_LOCATION:** CI-TEST-005 and CI-TEST-007 receipts
- **EXACT_PROOF:** T3_LINEAGE_DIGEST_STABLE=true; T4_REVERSE_TRACE_COMPLETE=true; T4_WHY_TRACE_COMPLETE=true; LINEAGE_AND_REVERSE_REFERENCES_STABLE=PASS
- **EVIDENCE_CLASS:** INTEGRATED / CONTROLLED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Trace / Provenance + History
- **GITHUB_DESTINATION:** Architecture / Lineage
- **STATUS:** VERIFIED_WITH_LABEL

### W1-C015
- **PUBLIC_CLAIM:** HYDRA uses contract/release-gate behavior that can block unresolved data.
- **SOURCE_ARTIFACT:** BEHAVIORAL_SEAM_RECEIPT.json; CI_TEST_006_REPAIRED_RERUN_SUMMARY_V002.txt
- **SOURCE_LOCATION:** CI-TEST-005/006 receipts
- **EXACT_PROOF:** T5_BLOCKER_IF_UNRESOLVED=true; T5_GATE_REASON_STABLE=true; T4_TO_T5_RELEASE_BLOCK_PATH=PASS
- **EVIDENCE_CLASS:** INTEGRATED / SYNTHETIC_SHADOW
- **PUBLIC_SAFE:** YES
- **NEEDS_REDACTION:** NO
- **WEBSITE_DESTINATION:** Contract-bound handoffs / Release Gates
- **GITHUB_DESTINATION:** Engineering principles / Release gates
- **STATUS:** VERIFIED_WITH_LABEL
