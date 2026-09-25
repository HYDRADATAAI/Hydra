# HYDRA Constraint Physical Policy Graph — Batch 003 Source Register

Companion to:

`HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH003_SOURCED_20260925.json`

The records below establish only identities and relationships directly needed for Batch 003 cross-layer validation.

| Source ID | Authority | Graph evidence |
|---|---|---|
| russia-government-2014-08-07-food-embargo | Government of the Russian Federation | covered food-import categories |
| ec-2022-04-08-fifth-restrictive-package | European Commission | Russian coal scope, Russian-flagged vessels, EU port-access scope |
| ec-2019-12-10-battery-ipcei | European Commission | battery IPCEI participating industrial projects and battery value-chain scope |
| panama-canal-a48-2023 | Panama Canal Authority | Panama Canal, Gatun water dependency, water-deficit bottleneck and transit context |
| ustr-2018-06-15-section301-list1 | USTR | Section 301 List 1 product group |
| ustr-2018-08-07-section301-list2 | USTR | Section 301 List 2 product group |
| ustr-2018-09-18-section301-list3 | USTR | Section 301 List 3 product group |
| wto-2014-08-29-rare-earths-dsb-adoption | WTO | rare earths, tungsten and molybdenum dispute resources |

A-54-2023 and the 2015 WTO implementation-status record remain policy/observation provenance and do not create new physical identities.

## Integrity

The existing sourced-graph loader verifies:

- source identity;
- HTTPS source URL;
- normalized-evidence SHA-256;
- historical source known date;
- node and edge identity uniqueness;
- endpoint integrity;
- provenance presence;
- point-in-time graph admission.

No broad physical-coverage claim is made from this bounded integration graph.
