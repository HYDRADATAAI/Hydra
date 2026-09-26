# Historical physical evidence source register

## U.S. refinery capacity — EIA

Authoritative source: U.S. Energy Information Administration (EIA), refinery capacity and utilization series.

- National January 1 operable atmospheric crude oil distillation capacity: https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=A&n=PET&s=8_NA_8D0_NUS_4
- Annual refinery utilization/capacity: https://www.eia.gov/dnav/pet/pet_pnp_unc_dcu_nus_a.htm
- Regional/PADD operable capacity: https://www.eia.gov/dnav/pet/PET_PNP_UNC_A_%28NA%29_YRL_MBBLPD_A.htm
- Refinery Capacity Report landing page: https://www.eia.gov/petroleum/refinerycapacity/index.php

### Temporal caution

The dataset separates the period a measurement describes from the date by which HYDRA should treat the observation as known. Annual-average utilization records therefore use a conservative following-year `known_at` rather than assuming the final annual statistic was available at the beginning of the measured year.

January 1 capacity observations are stored separately from annual-average utilization because they are different measurement concepts.

### Coverage status

This is the first sourced historical population slice. It demonstrates that the physical graph can carry real capacity history without fabricated observations. It does not imply energy-domain completeness.
