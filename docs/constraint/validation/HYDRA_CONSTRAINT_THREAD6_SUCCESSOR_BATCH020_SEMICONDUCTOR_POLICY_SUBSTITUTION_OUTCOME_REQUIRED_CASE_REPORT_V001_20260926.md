# HYDRA CONSTRAINT — Thread 6 Successor Batch 020 Policy / Substitution / Outcome / Required-Case Depth

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 019  
**Result:** `PASS_POLICY_SUBSTITUTION_OUTCOME_REQUIRED_CASE_DEPTH_PARTIAL`

Batch 020 executes the exact lane declared by Batch 019 and advances only cases supported by primary evidence.

## Case 7 — false beneficiary

Samsung is represented as a real HBM3E-capable producer. February 2024 evidence shows HBM3E 12H development/sampling with future mass production planned; April 2024 evidence shows HBM3E 8H mass production had begun.

That is **not enough** to qualify Samsung as a beneficiary of the bounded Micron/SK hynix HBM booked-supply constraint. Reviewed evidence does not establish:

- unbooked addressable Samsung capacity for the constrained target;
- required target-specific platform/customer qualification;
- switching time;
- realized economic/strategic capture.

The beneficiary is therefore fail-closed and Case 7 is covered by a real false-beneficiary rejection.

## Case 9 — export policy timing

The December 2024 BIS rule is represented with separate clocks:

```text
public inspection: 2024-12-02
effective_at:       2024-12-02
HBM compliance_at: 2024-12-31
HYDRA known_at:     current reviewed capture only
```

The historical legal dates are not promoted to Hydra historical knowledge. The event cannot enter a Hydra cutoff before `known_at`.

## Case 13 — failed/delayed capacity ramp

TSMC Arizona now has a preserved three-state ramp history:

```text
2020 announcement -> production targeted for 2024, 5nm, 20k wafers/month announced plan
2023 revision     -> N4 production pushed to 2025 because specialized equipment-installation labor was insufficient
2024 actual       -> N4 high-volume production in Q4 2024
```

The original 5nm / 20k-wafers-per-month announcement remains historical. It is never treated as realized N4 capacity.

## Still not covered

Case 10 substitution remains a gap. Samsung is a potential technical alternate, but qualified addressable capacity, switching time and realized relief are not proven.

Case 12 no-lookahead remains a gap for **historical replay**. Current-review `known_at` rules can block backward leakage, but original historical source-version availability is still not materialized.

## Truthful status

```ini
THREAD6_SUCCESSOR_BATCH020=PASS
NEW_REQUIRED_CASES_COVERED=7,9,13
REQUIRED_CASES_COVERED=5/14
FALSE_BENEFICIARIES_REJECTED=1
QUALIFIED_BENEFICIARIES_ADDED=0
QUALIFIED_SUBSTITUTIONS_ADDED=0
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-VALID-BENEFICIARY-SUBSTITUTION-MIGRATION-AND-CROSS-SLICE-POWER-DEPTH
```
