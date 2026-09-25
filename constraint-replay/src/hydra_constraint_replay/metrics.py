from math import sqrt
from .replay import replay_case

POSITIVE={"TRUE_POSITIVE","PARTIAL_REALIZATION","RIGHT_MECHANISM_WRONG_TIMING","RIGHT_CONSTRAINT_WRONG_BENEFICIARY"}
NEGATIVE={"FALSE_POSITIVE","TRUE_NEGATIVE"}
RESOLVED=POSITIVE|NEGATIVE|{"FALSE_NEGATIVE","INVALIDATED"}

def evaluate_cases(cases):
    rows=[replay_case(c) for c in cases]
    resolved=[(c,r) for c,r in zip(cases,rows) if r["outcome_class"] in RESOLVED]
    tp=sum(r["outcome_class"] in POSITIVE for _,r in resolved)
    fp=sum(r["outcome_class"]=="FALSE_POSITIVE" for _,r in resolved)
    fn=sum(r["outcome_class"]=="FALSE_NEGATIVE" for _,r in resolved)
    detected=tp+fp
    actual=tp+fn
    precision=None if not detected else tp/detected
    recall=None if not actual else tp/actual
    leads=[r["lead_time_days"] for _,r in resolved if r["lead_time_days"] is not None and r["lead_time_days"]>=0]
    brier_terms=[]
    for c,r in resolved:
        if c.outcome.realized_constraint is not None:
            y=1.0 if c.outcome.realized_constraint else 0.0
            brier_terms.append((c.hypothesis.confidence_at_t-y)**2)
    return {
        "case_count":len(cases),
        "resolved_count":len(resolved),
        "historical_coverage": None if not cases else len(resolved)/len(cases),
        "precision":precision,
        "recall_where_observable":recall,
        "false_positive_count":fp,
        "false_negative_count":fn,
        "mean_lead_time_days":None if not leads else sum(leads)/len(leads),
        "brier_score":None if not brier_terms else sum(brier_terms)/len(brier_terms),
        "provenance_completeness":None if not rows else sum(r["provenance_complete"] for r in rows)/len(rows),
        "lookahead_violation_count":sum(len(r["leakage_violations"]) for r in rows),
    }
