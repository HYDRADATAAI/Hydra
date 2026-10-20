from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from statistics import median

from .models import OUTCOME_CLASSES


class ClassifiedGoldError(ValueError):
    pass


CLASSIFIED_GOLD_TIER = "CLASSIFIED_GOLD_UNCALIBRATED"
NO_NUMERIC_CONFIDENCE = "NO_ADMISSIBLE_NUMERIC_CONFIDENCE"


def _dt(value: str, label: str) -> datetime:
    try:
        ts=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc:
        raise ClassifiedGoldError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ClassifiedGoldError(f"{label}: timezone-aware timestamp required")
    return ts


@dataclass(frozen=True)
class ClassifiedGoldRecord:
    case_id: str
    tier: str
    replay_t: datetime
    historical_hypothesis_source_ids: tuple[str,...]
    outcome_source_ids: tuple[str,...]
    outcome_first_observed_at: datetime
    outcome_class: str
    mapping_rule_set_id: str
    confidence_status: str
    confidence_evidence_ids: tuple[str,...]
    source_artifact_pins: tuple[tuple[str,str],...]

    def validate(self) -> None:
        if not self.case_id:
            raise ClassifiedGoldError("case_id required")
        if self.tier != CLASSIFIED_GOLD_TIER:
            raise ClassifiedGoldError(f"{self.case_id}: invalid classified-gold tier")
        if self.outcome_class not in OUTCOME_CLASSES:
            raise ClassifiedGoldError(f"{self.case_id}: unknown outcome class")
        if self.replay_t.tzinfo is None or self.replay_t.utcoffset() is None:
            raise ClassifiedGoldError(f"{self.case_id}: replay_t must be timezone-aware")
        if self.outcome_first_observed_at.tzinfo is None or self.outcome_first_observed_at.utcoffset() is None:
            raise ClassifiedGoldError(f"{self.case_id}: outcome timestamp must be timezone-aware")
        if self.outcome_first_observed_at <= self.replay_t:
            raise ClassifiedGoldError(f"{self.case_id}: outcome must be subsequent to replay_t")
        if not self.historical_hypothesis_source_ids or not self.outcome_source_ids:
            raise ClassifiedGoldError(f"{self.case_id}: hypothesis and outcome sources required")
        if len(self.historical_hypothesis_source_ids)!=len(set(self.historical_hypothesis_source_ids)):
            raise ClassifiedGoldError(f"{self.case_id}: duplicate hypothesis source IDs")
        if len(self.outcome_source_ids)!=len(set(self.outcome_source_ids)):
            raise ClassifiedGoldError(f"{self.case_id}: duplicate outcome source IDs")
        if self.confidence_status != NO_NUMERIC_CONFIDENCE:
            raise ClassifiedGoldError(f"{self.case_id}: unexpected confidence status")
        if not self.confidence_evidence_ids:
            raise ClassifiedGoldError(f"{self.case_id}: confidence audit evidence required")
        if not self.mapping_rule_set_id:
            raise ClassifiedGoldError(f"{self.case_id}: mapping rule set required")
        if not self.source_artifact_pins:
            raise ClassifiedGoldError(f"{self.case_id}: source artifact pins required")
        seen=set()
        for path,sha in self.source_artifact_pins:
            if not path or path in seen:
                raise ClassifiedGoldError(f"{self.case_id}: duplicate/empty source artifact path")
            seen.add(path)
            if len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha.lower()):
                raise ClassifiedGoldError(f"{self.case_id}: invalid Git blob SHA for {path}")


def load_classified_gold_corpus(path: str | Path) -> list[ClassifiedGoldRecord]:
    records=[]
    seen=set()
    with Path(path).open("r",encoding="utf-8") as fh:
        for lineno,line in enumerate(fh,1):
            if not line.strip():
                continue
            try:
                raw=json.loads(line)
            except json.JSONDecodeError as exc:
                raise ClassifiedGoldError(f"line {lineno}: invalid JSON") from exc
            record=ClassifiedGoldRecord(
                case_id=raw["case_id"],
                tier=raw["tier"],
                replay_t=_dt(raw["replay_t"],f"{raw.get('case_id','?')}.replay_t"),
                historical_hypothesis_source_ids=tuple(raw["historical_hypothesis_source_ids"]),
                outcome_source_ids=tuple(raw["outcome_source_ids"]),
                outcome_first_observed_at=_dt(
                    raw["outcome_first_observed_at"],
                    f"{raw.get('case_id','?')}.outcome_first_observed_at",
                ),
                outcome_class=raw["outcome_class"],
                mapping_rule_set_id=raw["mapping_rule_set_id"],
                confidence_status=raw["confidence_status"],
                confidence_evidence_ids=tuple(raw["confidence_evidence_ids"]),
                source_artifact_pins=tuple(
                    (x["path"],x["git_blob_sha"]) for x in raw["source_artifact_pins"]
                ),
            )
            record.validate()
            if record.case_id in seen:
                raise ClassifiedGoldError(f"duplicate case_id {record.case_id}")
            seen.add(record.case_id)
            records.append(record)
    if not records:
        raise ClassifiedGoldError("classified-gold corpus is empty")
    return records


def summarize_classified_gold(records: list[ClassifiedGoldRecord]) -> dict:
    leads=[
        (r.outcome_first_observed_at-r.replay_t).total_seconds()/86400
        for r in records
    ]
    classes={}
    for r in records:
        classes[r.outcome_class]=classes.get(r.outcome_class,0)+1
    return {
        "case_count":len(records),
        "outcome_class_counts":classes,
        "mean_lead_time_days":sum(leads)/len(leads),
        "median_lead_time_days":median(leads),
        "calibrated_case_count":0,
        "brier_score":None,
    }
