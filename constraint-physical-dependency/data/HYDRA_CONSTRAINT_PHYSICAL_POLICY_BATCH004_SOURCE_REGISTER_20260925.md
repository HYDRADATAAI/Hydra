# HYDRA Constraint Physical Policy Graph — Batch 004 Source Register

Companion to:

`HYDRA_CONSTRAINT_PHYSICAL_POLICY_GRAPH_BATCH004_SOURCED_20260925.json`

## Sources

| Source ID | Authority | Physical evidence admitted |
|---|---|---|
| wto-2019-07-10-japan-korea-goods-council | World Trade Organization | generic technology-production input constraint and Korean semiconductor/display manufacturing context |
| wto-ds590-2019-09-16 | World Trade Organization | later named material identities; retained as policy/observation provenance rather than leaked into July event |
| consilium-2019-11-11-eastmed-framework | Council of the EU | offshore hydrocarbon resource/drilling identities and Cyprus-referenced location context |
| bnetza-2021-11-16-nordstream2-suspension | Bundesnetzagentur | Nord Stream 2 pipeline, operator and gas-transport certification context |
| govinfo-2022-08-16-pl117-169-45x | U.S. Government Publishing Office | section 45X manufacturing, eligible-component and critical-mineral identities |
| bmwk-2022-12-17-wilhelmshaven-opening | German Federal Ministry for Economic Affairs and Climate Action | Wilhelmshaven FSRU, direct LNG import path and ~5 bcm/year regasification capacity |

The 22 February 2022 BMWK Nord Stream record is a later policy-state source and does not create a new physical identity. The 2023 Treasury 45X source and 2023 Uniper operating-status source are later observations.

## Capacity admission

Batch 004 makes the sourced loader consume optional capacity/share fields already represented by the physical model.

Numeric values are rejected when:
- nonnumeric;
- negative where nonnegative is required;
- outside [0,1] for fractions;
- paired with an invalid capacity-unit representation;
- invalid as substitution lead-time integers.

This is a bounded ingestion improvement, not a claim that every historical graph node now has quantitative capacity data.
