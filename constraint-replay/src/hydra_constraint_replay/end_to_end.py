from __future__ import annotations

from datetime import datetime
from hashlib import sha1, sha256
import json
from pathlib import Path
from statistics import median
from typing import Any

from .classified_gold import load_classified_gold_corpus
from .corpus import load_replay_ready_corpus, summarize_replay_ready_corpus
from .promotion import evaluate_promotion, load_promotion_audits, summarize_promotion


class EndToEndReplayError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return sha1(f"blob {len(payload)}\0".encode()+payload).hexdigest()


def _stable_digest(value: Any) -> str:
    return sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()
    ).hexdigest()


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if not 0 <= q <= 1:
        raise EndToEndReplayError("percentile q outside [0,1]")
    ordered=sorted(values)
    if len(ordered)==1:
        return ordered[0]
    pos=(len(ordered)-1)*q
    lo=int(pos)
    hi=min(lo+1,len(ordered)-1)
    frac=pos-lo
    return ordered[lo]*(1-frac)+ordered[hi]*frac


def run_classified_replay_e2e(
    repo_root: str | Path,
    replay_ready_path: str | Path,
    classified_gold_path: str | Path,
    promotion_audit_path: str | Path,
) -> dict:
    root=Path(repo_root)
    replay_path=root/Path(replay_ready_path)
    classified_path=root/Path(classified_gold_path)
    promotion_path=root/Path(promotion_audit_path)

    replay_records=load_replay_ready_corpus(replay_path)
    classified_records=load_classified_gold_corpus(classified_path)
    audits=load_promotion_audits(promotion_path)

    replay_ids={r["case_id"] for r in replay_records}
    classified_ids={r.case_id for r in classified_records}
    audit_ids={a.case_id for a in audits}
    if replay_ids != classified_ids:
        raise EndToEndReplayError("classified case set does not equal replay-ready case set")
    if replay_ids != audit_ids:
        raise EndToEndReplayError("promotion-audit case set does not equal replay-ready case set")

    replay_by={r["case_id"]:r for r in replay_records}
    classified_by={r.case_id:r for r in classified_records}
    audit_by={a.case_id:a for a in audits}

    # Revalidate every source-bundle pin and every classified artifact pin.
    source_bundle_cache: dict[str,str]={}
    pinned_artifact_cache: dict[str,str]={}
    for record in replay_records:
        source_path=record["source_bundle"]
        if source_path not in source_bundle_cache:
            source_bundle_cache[source_path]=_git_blob_sha(root/source_path)
        if source_bundle_cache[source_path] != record["source_bundle_blob_sha"]:
            raise EndToEndReplayError(
                f"{record['case_id']}: replay source bundle pin mismatch"
            )

    for record in classified_records:
        for relative_path,expected_sha in record.source_artifact_pins:
            if relative_path not in pinned_artifact_cache:
                pinned_artifact_cache[relative_path]=_git_blob_sha(root/relative_path)
            if pinned_artifact_cache[relative_path] != expected_sha:
                raise EndToEndReplayError(
                    f"{record.case_id}: classified artifact pin mismatch for {relative_path}"
                )

    rows=[]
    leads=[]
    for case_id in sorted(replay_ids):
        rr=replay_by[case_id]
        cg=classified_by[case_id]
        audit=audit_by[case_id]
        decision=evaluate_promotion(audit)

        if not decision.classified_gold_uncalibrated_eligible:
            raise EndToEndReplayError(f"{case_id}: classified record is not promotion-eligible")
        if decision.classification_blockers:
            raise EndToEndReplayError(f"{case_id}: classification blockers remain")
        if decision.scored_gold_eligible:
            raise EndToEndReplayError(
                f"{case_id}: calibrated/scored case unexpectedly present in uncalibrated run"
            )
        if audit.proposed_outcome_class != cg.outcome_class:
            raise EndToEndReplayError(f"{case_id}: promotion/classified outcome mismatch")

        lead_days=(cg.outcome_first_observed_at-cg.replay_t).total_seconds()/86400
        if lead_days <= 0:
            raise EndToEndReplayError(f"{case_id}: nonpositive outcome evidence lead")
        leads.append(lead_days)

        cuts=rr["replay_cuts"]
        rows.append({
            "case_id":case_id,
            "replay_cut_count":len(cuts),
            "first_replay_cut":cuts[0]["replay_t"],
            "last_replay_cut":cuts[-1]["replay_t"],
            "classified_replay_t":cg.replay_t.isoformat(),
            "outcome_first_observed_at":cg.outcome_first_observed_at.isoformat(),
            "evidence_availability_lead_days":lead_days,
            "outcome_class":cg.outcome_class,
            "classification_stage":decision.stage.value,
            "calibration_blockers":list(decision.calibration_blockers),
            "calibrated":False,
        })

    replay_summary=summarize_replay_ready_corpus(replay_records)
    promotion_summary=summarize_promotion(audits)

    outcome_counts: dict[str,int]={}
    for row in rows:
        outcome_counts[row["outcome_class"]]=outcome_counts.get(row["outcome_class"],0)+1

    body={
        "schema_version":"1.0",
        "run_kind":"HYDRA_CONSTRAINT_CLASSIFIED_REPLAY_E2E",
        "run_status":"PASS",
        "inputs":{
            "replay_ready":{
                "path":str(Path(replay_ready_path)),
                "git_blob_sha":_git_blob_sha(replay_path),
            },
            "classified_gold":{
                "path":str(Path(classified_gold_path)),
                "git_blob_sha":_git_blob_sha(classified_path),
            },
            "promotion_audit":{
                "path":str(Path(promotion_audit_path)),
                "git_blob_sha":_git_blob_sha(promotion_path),
            },
        },
        "coverage":{
            "case_count":len(rows),
            "replay_cut_count":replay_summary.replay_cut_count,
            "event_id_count":replay_summary.event_id_count,
            "observation_id_count":replay_summary.observation_id_count,
            "classification_coverage":1.0 if rows else None,
            "classified_gold_uncalibrated_count":promotion_summary[
                "classified_gold_uncalibrated_count"
            ],
            "calibrated_case_count":promotion_summary["score_ready_count"],
        },
        "outcomes":{
            "class_counts":outcome_counts,
            "resolved_or_classified_count":len(rows),
            "unevaluable_count":outcome_counts.get("UNEVALUABLE",0),
        },
        "lead_time_days":{
            "mean":sum(leads)/len(leads),
            "median":median(leads),
            "minimum":min(leads),
            "p25":_percentile(leads,0.25),
            "p75":_percentile(leads,0.75),
            "maximum":max(leads),
        },
        "calibration":{
            "status":"BLOCKED_NO_ADMISSIBLE_NUMERIC_CONFIDENCE",
            "calibrated_case_count":0,
            "brier_score":None,
            "common_blockers":[
                "NO_PRECOMMITTED_CONFIDENCE_SOURCE",
                "NO_SOURCE_GROUNDED_CONFIDENCE_VALUE",
            ],
        },
        "integrity":{
            "replay_ready_case_set_equals_classified_case_set":True,
            "replay_ready_case_set_equals_promotion_case_set":True,
            "replay_source_bundle_pins_valid":True,
            "classified_artifact_pins_valid":True,
            "classification_blockers_remaining":0,
            "calibrated_cases_present":0,
        },
        "cases":rows,
    }
    return {**body,"run_digest_sha256":_stable_digest(body)}
