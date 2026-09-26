from statistics import median
from .replay import replay_case

DETECTED_POSITIVE={"TRUE_POSITIVE","PARTIAL_REALIZATION","RIGHT_MECHANISM_WRONG_TIMING","RIGHT_CONSTRAINT_WRONG_BENEFICIARY"}
RESOLVED=DETECTED_POSITIVE|{"FALSE_POSITIVE","TRUE_NEGATIVE","FALSE_NEGATIVE","INVALIDATED"}

def evaluate_cases(cases):
    rows=[replay_case(c) for c in cases]
    resolved=[(c,r) for c,r in zip(cases,rows) if r["outcome_class"] in RESOLVED]
    tp=sum(r["outcome_class"] in DETECTED_POSITIVE for _,r in resolved)
    fp=sum(r["outcome_class"]=="FALSE_POSITIVE" for _,r in resolved)
    tn=sum(r["outcome_class"]=="TRUE_NEGATIVE" for _,r in resolved)
    fn=sum(r["outcome_class"]=="FALSE_NEGATIVE" for _,r in resolved)
    precision=None if tp+fp==0 else tp/(tp+fp)
    recall=None if tp+fn==0 else tp/(tp+fn)
    fpr=None if fp+tn==0 else fp/(fp+tn)
    leads=[r["lead_time_days"] for _,r in resolved if r["lead_time_days"] is not None]
    brier=[]
    for c,_ in resolved:
        if c.outcome.realized_constraint is not None:
            y=float(c.outcome.realized_constraint)
            brier.append((c.hypothesis.confidence_at_t-y)**2)
    return {
        "case_count":len(cases),
        "resolved_count":len(resolved),
        "historical_coverage":None if not cases else len(resolved)/len(cases),
        "precision":precision,
        "recall_where_observable":recall,
        "false_positive_rate":fpr,
        "false_positive_count":fp,
        "false_negative_count":fn,
        "mean_lead_time_days":None if not leads else sum(leads)/len(leads),
        "median_lead_time_days":None if not leads else median(leads),
        "brier_score":None if not brier else sum(brier)/len(brier),
        "provenance_completeness":None if not rows else sum(r["provenance_complete"] for r in rows)/len(rows),
        "lookahead_violation_count":sum(len(r["leakage_violations"]) for r in rows),
    }
