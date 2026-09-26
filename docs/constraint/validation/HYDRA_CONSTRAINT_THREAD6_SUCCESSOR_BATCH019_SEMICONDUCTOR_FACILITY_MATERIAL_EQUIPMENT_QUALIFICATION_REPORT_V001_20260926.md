# HYDRA CONSTRAINT — Thread 6 Successor Batch 019 Facility / Material / Equipment / Qualification Deepening

**Slice:** `SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_V1`  
**Predecessor:** Batch 018  
**Result:** `PASS_FACILITY_MATERIAL_EQUIPMENT_QUALIFICATION_DEEPENING_PARTIAL`

Batch 019 executes the exact next lane declared by the merged Batch 018. It deepens the second slice without changing Constraint ownership or creating semiconductor-only semantics.

## Added facility population

- TSMC Advanced Backend Fab 6 in Zhunan: advanced packaging/test capability with company-stated design-capacity estimates kept separate from available capacity.
- TSMC Arizona first fab: 2023 installation/ramp plan preserved separately from the observed Q4 2024 N4 high-volume-production outcome.
- Amkor Vietnam in Bac Ninh: opened in October 2023 as a phased advanced packaging/test facility; planned cleanroom area is not treated as production throughput.

## Added geology / material chain

```text
silica / quartzite
-> silicon metal
-> high-purity polysilicon
-> CZ monocrystalline ingot
-> silicon wafer
-> semiconductor device
```

The chain deliberately preserves the firewall between broad geological/resource supply and semiconductor-grade processed material. USGS's broad 2023 silicon-material production concentration is not reinterpreted as semiconductor-grade wafer concentration.

## Added equipment and policy access

ASML NXT:2050i and NXT:2100i are represented as DUV immersion lithography equipment. The January 2024 partial shipment-license revocation is a bounded policy-access event; it is not represented as a complete China cutoff and its exact effective timestamp remains unresolved.

## Qualification

NVIDIA's disclosed new-product qualification time is represented as an unquantified timing dependency. Micron's Batch 018 in-progress HBM3E qualification observation is reused rather than duplicated.

## Outcome corpus

The first semiconductor shadow outcome is now present:

- 2023 plan: Arizona N4 volume production targeted for 2025 H1.
- observed successor state: N4 high-volume production in 2024 Q4, reported by TSMC as earlier than scheduled.

This is current-review outcome evidence, not historical replay evidence.

## Required cases

No additional case is falsely closed. Cases 4, 5, 6 and 9 now have better prerequisite population, but remain gaps because their full expected behavior is not yet proven. Coverage stays **2/14**.

```ini
THREAD6_SUCCESSOR_BATCH019=PASS
FACILITIES_ADDED=3
EQUIPMENT_NODES_ADDED=2
MATERIAL_STAGE_NODES_ADDED=6
QUALIFICATION_OBSERVATIONS_ADDED=2
DEPENDENCY_EDGES_ADDED=29
OUTCOMES_CAPTURED_SHADOW=1
REQUIRED_CASES_COVERED=2/14
HISTORICAL_REPLAY=BLOCKED
FIRST_SEMICONDUCTOR_RUN=BLOCKED
NEXT_REPO_EXECUTABLE_LANE=SECOND-SLICE-POLICY-SUBSTITUTION-OUTCOME-AND-REQUIRED-CASE-DEPTH
```
