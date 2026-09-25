# HYDRA ML Spine v0.3 Acceptance Gate Draft

Gate requirements:
- v0.3 design contract exists
- selected inputs exist
- source schema checked
- leakage audit updated
- label quality acceptable
- runtime estimate done
- no source mutation
- no planner model-score attachment
- explicit run authorization by lane logic

Blocking conditions:
- missing source schema
- unresolved label ambiguity
- leakage risk
- huge runtime without approval
- any request to attach scores to planner
