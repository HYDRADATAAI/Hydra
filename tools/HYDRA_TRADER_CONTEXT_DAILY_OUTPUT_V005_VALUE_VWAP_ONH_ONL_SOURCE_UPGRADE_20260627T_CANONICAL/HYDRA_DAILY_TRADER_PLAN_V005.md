# HYDRA Daily Trader Plan V005

Baby ML status: `FROZEN`
Hidden-gem input: `/workspace/HYDRA/tmp_v005_fixture/hidden`
V003 input: `/workspace/HYDRA/tmp_v005_fixture/v003`

# ES Daily Plan V005

Session date: `2025-03-26`
Source: `/workspace/HYDRA/tmp_v005_fixture/source/es_context.csv`

Render law: every sentence is sourced, deterministically derived, coach-rule conditional, or an explicit missing-source caveat.

dOpen:
- ES session open: 20083.25.
- Prior value: open is INSIDE pdVA; pdVAH 20110, pdPOC 20095, pdVAL 20080.
- Value quartile: LOWER_QUARTILE.
- Prior range: open is inside prior range; PDH 20129.25, PDL 20076.5.
- Gap: GAP_DOWN / direction DOWN; points -0.5, percent null.
- VWAP: daily_vwap sourced at 20100; price_vs_daily_vwap=ABOVE.
- Overnight: ONH 20140, ONL 20070; sweep/reclaim logic may be described only with chart confirmation.

Context:
- Current/latest price: 20124.5 from `/workspace/HYDRA/tmp_v005_fixture/source/es_context.csv`.
- Prior-day value is available: pdVAH 20110, pdPOC 20095, pdVAL 20080; price_vs_pdVAH=ABOVE, price_vs_pdVAL=ABOVE.
- Higher-timeframe value: pwVAH 20160, pwPOC 20100, pwVAL 19570; pmVAH 20490, pmPOC 20460, pmVAL 20420.
- VWAP context: daily_vwap 20100; relation ABOVE.
- Overnight context: ONH 20140, ONL 20070.
- MISSING: session_context missing; London/NY behavior classification disabled.
- Rendered posture: confirmation-first; sourced fields may guide reactions, missing fields block confidence.

Longs:
- MISSING: no ranked/selected first long level source; do not claim a first level.
- VWAP condition: only consider long logic after chart-confirmed reclaim around daily_vwap 20100.
- Value condition: use pdVA boundaries as reaction references only; acceptance/rejection requires chart/export confirmation.
- Size guidance: conservative/unknown until level-quality source exists.

Shorts:
- MISSING: no ranked/selected first short level source; do not claim a first level.
- VWAP condition: only consider short logic after chart-confirmed rejection/loss around daily_vwap 20100.
- Value condition: use pdVA boundaries as reaction references only; acceptance/rejection requires chart/export confirmation.
- Size guidance: conservative/unknown until level-quality source exists.

Missing source warnings:
- first_long_level_of_interest missing; do not claim first level; list nearby references only.
- first_short_level_of_interest missing; do not claim first level; list nearby references only.
- session_context missing; London/NY behavior classification disabled.
- level_quality_source missing; size guidance remains conservative/unknown.
- dealer/gamma source missing; gamma/call wall/put wall/vol trigger logic disabled.

Terminal:
HYDRA_TRADER_CONTEXT_DAILY_OUTPUT_V005_VALUE_VWAP_ONH_ONL_SOURCE_UPGRADE_COMPLETE_BABY_ML_FROZEN


---

# NQ Daily Plan V005

Session date: `2025-03-26`
Source: `/workspace/HYDRA/tmp_v005_fixture/source/nq_context.csv`

Render law: every sentence is sourced, deterministically derived, coach-rule conditional, or an explicit missing-source caveat.

dOpen:
- NQ session open: 20101.75.
- Prior value: open is INSIDE pdVA; pdVAH 20115, pdPOC 20100, pdVAL 20085.
- Value quartile: MID_VALUE.
- Prior range: open is inside prior range; PDH 20129.25, PDL 20076.5.
- Gap: GAP_UP / direction UP; points 0.5, percent null.
- VWAP: daily_vwap sourced at 20105; price_vs_daily_vwap=BELOW.
- Overnight: ONH 20150, ONL 20080; sweep/reclaim logic may be described only with chart confirmation.

Context:
- Current/latest price: 20096.25 from `/workspace/HYDRA/tmp_v005_fixture/source/nq_context.csv`.
- Prior-day value is available: pdVAH 20115, pdPOC 20100, pdVAL 20085; price_vs_pdVAH=BELOW, price_vs_pdVAL=ABOVE.
- Higher-timeframe value: pwVAH 20165, pwPOC 20105, pwVAL 19575; pmVAH 20495, pmPOC 20465, pmVAL 20425.
- VWAP context: daily_vwap 20105; relation BELOW.
- Overnight context: ONH 20150, ONL 20080.
- MISSING: session_context missing; London/NY behavior classification disabled.
- Rendered posture: confirmation-first; sourced fields may guide reactions, missing fields block confidence.

Longs:
- MISSING: no ranked/selected first long level source; do not claim a first level.
- VWAP condition: only consider long logic after chart-confirmed reclaim around daily_vwap 20105.
- Value condition: use pdVA boundaries as reaction references only; acceptance/rejection requires chart/export confirmation.
- Size guidance: conservative/unknown until level-quality source exists.

Shorts:
- MISSING: no ranked/selected first short level source; do not claim a first level.
- VWAP condition: only consider short logic after chart-confirmed rejection/loss around daily_vwap 20105.
- Value condition: use pdVA boundaries as reaction references only; acceptance/rejection requires chart/export confirmation.
- Size guidance: conservative/unknown until level-quality source exists.

Missing source warnings:
- first_long_level_of_interest missing; do not claim first level; list nearby references only.
- first_short_level_of_interest missing; do not claim first level; list nearby references only.
- session_context missing; London/NY behavior classification disabled.
- level_quality_source missing; size guidance remains conservative/unknown.
- dealer/gamma source missing; gamma/call wall/put wall/vol trigger logic disabled.

Terminal:
HYDRA_TRADER_CONTEXT_DAILY_OUTPUT_V005_VALUE_VWAP_ONH_ONL_SOURCE_UPGRADE_COMPLETE_BABY_ML_FROZEN


---

# Igor-Style Daily Recap & Preparation V005

Market Context:
- ES: latest price 20124.5; open_vs_pdVA INSIDE; daily_vwap 20100.
- NQ: latest price 20096.25; open_vs_pdVA INSIDE; daily_vwap 20105.

Overnight:
- ES: ONH 20140, ONL 20070.
- NQ: ONH 20150, ONL 20080.

Dealer Positioning:
- MISSING: dealer/gamma data not part of V005 source upgrade; call wall, put wall, vol trigger logic disabled.

Discipline:
- No chase. No invented first levels. Use sourced references only and wait for confirmation.

Terminal:
HYDRA_TRADER_CONTEXT_DAILY_OUTPUT_V005_VALUE_VWAP_ONH_ONL_SOURCE_UPGRADE_COMPLETE_BABY_ML_FROZEN
