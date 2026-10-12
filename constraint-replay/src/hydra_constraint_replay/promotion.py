from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Iterable


class PromotionError(ValueError):
    pass


class OutcomeEvidenceLevel(str, Enum):
    NONE = "NONE"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    SCORABLE_CANDIDATE_QUALITATIVE = "SCORABLE_CANDIDATE_QUALITATIVE"
    SCORABLE_CANDIDATE_QUANTITATIVE = "SCORABLE_CANDIDATE_QUANTITATIVE"
    SCORABLE_CANDIDATE_OPERATIONAL = "SCORABLE_CANDIDATE_OPERATIONAL"


class PromotionStage(str, Enum):
    REPLAY_READY_ONLY = "REPLAY_READY_ONLY"
    OUTCOME_EVIDENCE_PRESENT = "OUTCOME_EVIDENCE_PRESENT"
    HYPOTHESIS_EVIDENCE_PRESENT = "HYPOTHESIS_EVIDENCE_PRESENT"
    CLASSIFIED_GOLD_UNCALIBRATED = "CLASSIFIED_GOLD_UNCALIBRATED"
    CONFIDENCE_EVIDENCE_PRESENT = "CONFIDENCE_EVIDENCE_PRESENT"
    SCORE_READY = "SCORE_READY"


REQUIRED_GOLD_FIELDS = (
    "historical_hypothesis_source_ids",
    "historical_confidence_source_ids",
    "outcome_source_ids",
)


@dataclass(frozen=True)
class PromotionAudit:
    case_id: str
    replay_tier: str
    historical_hypothesis_source_ids: tuple[str, ...]
    historical_confidence_source_ids: tuple[str, ...]
    outcome_source_ids: tuple[str, ...]
    outcome_evidence_level: OutcomeEvidenceLevel
    outcome_class_supported: bool
    proposed_confidence_at_t: float | None = None
    proposed_outcome_class: str | None = None

    def validate(self) -> None:
        if not self.case_id:
            raise PromotionError("case_id required")
        if self.replay_tier != "REPLAY_READY_UNSCORED":
            raise PromotionError(f"{self.case_id}: unexpected replay tier {self.replay_tier!r}")
        for field_name in REQUIRED_GOLD_FIELDS:
            value=getattr(self,field_name)
            if len(value)!=len(set(value)):
                raise PromotionError(f"{self.case_id}: duplicate IDs in {field_name}")
            if any(not isinstance(x,str) or not x for x in value):
                raise PromotionError(f"{self.case_id}: invalid source ID in {field_name}")
        if self.outcome_evidence_level == OutcomeEvidenceLevel.NONE and self.outcome_source_ids:
            raise PromotionError(f"{self.case_id}: NONE outcome level cannot have outcome sources")
        if self.outcome_evidence_level != OutcomeEvidenceLevel.NONE and not self.outcome_source_ids:
            raise PromotionError(f"{self.case_id}: outcome evidence level requires outcome sources")
        if self.proposed_confidence_at_t is not None:
            if not 0 <= self.proposed_confidence_at_t <= 1:
                raise PromotionError(f"{self.case_id}: proposed confidence outside [0,1]")
            if not self.historical_confidence_source_ids:
                raise PromotionError(f"{self.case_id}: confidence value requires historical confidence source")
        if self.proposed_outcome_class is not None and not self.outcome_class_supported:
            raise PromotionError(f"{self.case_id}: outcome class supplied without support")
        if self.outcome_class_supported and not self.outcome_source_ids:
            raise PromotionError(f"{self.case_id}: outcome class support requires outcome evidence")
        if self.outcome_class_supported and self.proposed_outcome_class is None:
            raise PromotionError(f"{self.case_id}: supported outcome class must be explicit")


@dataclass(frozen=True)
class PromotionDecision:
    case_id: str
    stage: PromotionStage
    blockers: tuple[str, ...]
    classification_blockers: tuple[str, ...]
    calibration_blockers: tuple[str, ...]
    classified_gold_uncalibrated_eligible: bool
    scored_gold_eligible: bool


def evaluate_promotion(audit: PromotionAudit) -> PromotionDecision:
    audit.validate()

    classification_blockers=[]
    if not audit.historical_hypothesis_source_ids:
        classification_blockers.append("NO_INDEPENDENT_HISTORICAL_HYPOTHESIS_SOURCE")
    if not audit.outcome_source_ids:
        classification_blockers.append("NO_OUTCOME_OBSERVATION_IN_CASE_BUNDLE")
    if not audit.outcome_class_supported:
        classification_blockers.append("OUTCOME_NOT_MAPPED_TO_SCORABLE_CLASS")
    if audit.proposed_outcome_class is None:
        classification_blockers.append("NO_SUPPORTED_OUTCOME_CLASS")

    calibration_blockers=[]
    if not audit.historical_confidence_source_ids:
        calibration_blockers.append("NO_PRECOMMITTED_CONFIDENCE_SOURCE")
    if audit.proposed_confidence_at_t is None:
        calibration_blockers.append("NO_SOURCE_GROUNDED_CONFIDENCE_VALUE")

    classified=not classification_blockers
    scored=classified and not calibration_blockers
    blockers=tuple(classification_blockers+calibration_blockers)

    if scored:
        stage=PromotionStage.SCORE_READY
    elif audit.historical_confidence_source_ids:
        stage=PromotionStage.CONFIDENCE_EVIDENCE_PRESENT
    elif classified:
        stage=PromotionStage.CLASSIFIED_GOLD_UNCALIBRATED
    elif audit.historical_hypothesis_source_ids:
        stage=PromotionStage.HYPOTHESIS_EVIDENCE_PRESENT
    elif audit.outcome_source_ids:
        stage=PromotionStage.OUTCOME_EVIDENCE_PRESENT
    else:
        stage=PromotionStage.REPLAY_READY_ONLY

    return PromotionDecision(
        case_id=audit.case_id,
        stage=stage,
        blockers=blockers,
        classification_blockers=tuple(classification_blockers),
        calibration_blockers=tuple(calibration_blockers),
        classified_gold_uncalibrated_eligible=classified,
        scored_gold_eligible=scored,
    )


def assert_classified_gold_eligible(audit: PromotionAudit) -> None:
    decision=evaluate_promotion(audit)
    if not decision.classified_gold_uncalibrated_eligible:
        raise PromotionError(
            f"{audit.case_id}: classified-gold promotion blocked: "
            f"{', '.join(decision.classification_blockers)}"
        )


def assert_scored_gold_eligible(audit: PromotionAudit) -> None:
    decision=evaluate_promotion(audit)
    if not decision.scored_gold_eligible:
        raise PromotionError(
            f"{audit.case_id}: scored-gold promotion blocked: {', '.join(decision.blockers)}"
        )


def audit_from_dict(raw: dict) -> PromotionAudit:
    try:
        audit=PromotionAudit(
            case_id=raw["case_id"],
            replay_tier=raw["replay_tier"],
            historical_hypothesis_source_ids=tuple(raw.get("historical_hypothesis_source_ids",[])),
            historical_confidence_source_ids=tuple(raw.get("historical_confidence_source_ids",[])),
            outcome_source_ids=tuple(raw.get("outcome_source_ids",[])),
            outcome_evidence_level=OutcomeEvidenceLevel(raw.get("outcome_evidence_level","NONE")),
            outcome_class_supported=bool(raw.get("outcome_class_supported",False)),
            proposed_confidence_at_t=raw.get("proposed_confidence_at_t"),
            proposed_outcome_class=raw.get("proposed_outcome_class"),
        )
    except (KeyError,ValueError,TypeError) as exc:
        raise PromotionError("invalid promotion audit record") from exc
    audit.validate()
    return audit


def load_promotion_audits(path: str | Path) -> list[PromotionAudit]:
    raw=json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version") != "1.0":
        raise PromotionError("unsupported promotion-audit schema")
    audits=[]
    seen=set()
    for item in raw.get("cases",[]):
        audit=audit_from_dict(item)
        if audit.case_id in seen:
            raise PromotionError(f"duplicate case_id {audit.case_id}")
        seen.add(audit.case_id)
        audits.append(audit)
    if not audits:
        raise PromotionError("promotion audit is empty")
    return audits


def summarize_promotion(audits: Iterable[PromotionAudit]) -> dict:
    audits=list(audits)
    decisions=[evaluate_promotion(a) for a in audits]
    return {
        "case_count":len(audits),
        "classified_gold_uncalibrated_count":sum(
            d.classified_gold_uncalibrated_eligible for d in decisions
        ),
        "score_ready_count":sum(d.scored_gold_eligible for d in decisions),
        "outcome_evidence_present_count":sum(bool(a.outcome_source_ids) for a in audits),
        "outcome_class_supported_count":sum(a.outcome_class_supported for a in audits),
        "scorable_candidate_outcome_count":sum(
            a.outcome_evidence_level in {
                OutcomeEvidenceLevel.SCORABLE_CANDIDATE_QUALITATIVE,
                OutcomeEvidenceLevel.SCORABLE_CANDIDATE_QUANTITATIVE,
                OutcomeEvidenceLevel.SCORABLE_CANDIDATE_OPERATIONAL,
            }
            for a in audits
        ),
        "independent_hypothesis_present_count":sum(bool(a.historical_hypothesis_source_ids) for a in audits),
        "confidence_source_present_count":sum(bool(a.historical_confidence_source_ids) for a in audits),
        "stages":{stage.value:sum(d.stage==stage for d in decisions) for stage in PromotionStage},
    }
