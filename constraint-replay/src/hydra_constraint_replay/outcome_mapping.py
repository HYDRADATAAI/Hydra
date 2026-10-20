from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


class OutcomeMappingError(ValueError):
    pass


POSITIVE_CONSTRAINT_RULESET_V1 = "POSITIVE_CONSTRAINT_RULESET_V1"
SUPPORTED_OUTCOME_CLASSES = {
    "TRUE_POSITIVE",
    "FALSE_POSITIVE",
    "PARTIAL_REALIZATION",
    "RIGHT_MECHANISM_WRONG_TIMING",
    "INVALIDATED",
    "UNEVALUABLE",
}


@dataclass(frozen=True)
class OutcomeMappingInputs:
    case_id: str
    rule_set_id: str
    mechanism_observed: bool
    direction_consistent: bool
    explicit_numeric_target_defined: bool
    target_met: bool | None
    explicit_horizon_defined: bool
    horizon_met: bool | None
    causal_attribution_clean: bool
    outcome_observation_complete: bool
    contradiction_open: bool
    evidence_source_ids: tuple[str, ...]
    rationale: str

    def validate(self) -> None:
        if not self.case_id or self.rule_set_id != POSITIVE_CONSTRAINT_RULESET_V1:
            raise OutcomeMappingError(f"{self.case_id or '<missing>'}: unsupported mapping rule set")
        for field in (
            "mechanism_observed","direction_consistent","explicit_numeric_target_defined",
            "explicit_horizon_defined","causal_attribution_clean",
            "outcome_observation_complete","contradiction_open",
        ):
            if type(getattr(self,field)) is not bool:
                raise OutcomeMappingError(f"{self.case_id}: {field} must be boolean")
        if self.explicit_numeric_target_defined and self.target_met is None:
            raise OutcomeMappingError(f"{self.case_id}: target_met required when target is defined")
        if not self.explicit_numeric_target_defined and self.target_met is not None:
            raise OutcomeMappingError(f"{self.case_id}: target_met forbidden without explicit target")
        if (
            self.explicit_horizon_defined
            and self.horizon_met is None
            and self.outcome_observation_complete
        ):
            raise OutcomeMappingError(
                f"{self.case_id}: horizon_met required when a defined horizon has a complete outcome window"
            )
        if not self.explicit_horizon_defined and self.horizon_met is not None:
            raise OutcomeMappingError(f"{self.case_id}: horizon_met forbidden without explicit horizon")
        if not self.evidence_source_ids or len(self.evidence_source_ids)!=len(set(self.evidence_source_ids)):
            raise OutcomeMappingError(f"{self.case_id}: unique evidence_source_ids required")
        if not self.rationale:
            raise OutcomeMappingError(f"{self.case_id}: rationale required")


@dataclass(frozen=True)
class OutcomeMappingDecision:
    case_id: str
    rule_set_id: str
    outcome_class: str
    rationale_code: str


def map_positive_constraint_outcome(inputs: OutcomeMappingInputs) -> OutcomeMappingDecision:
    """Apply a mechanism-generic mapping declared before case class assignment.

    This function does not use confidence values and does not compute a score.
    It only maps an evidence state into the existing replay outcome taxonomy.
    """
    inputs.validate()

    if inputs.contradiction_open or not inputs.outcome_observation_complete:
        return OutcomeMappingDecision(
            inputs.case_id,inputs.rule_set_id,"UNEVALUABLE",
            "OPEN_CONTRADICTION_OR_INCOMPLETE_OUTCOME_WINDOW",
        )

    if not inputs.mechanism_observed:
        return OutcomeMappingDecision(
            inputs.case_id,inputs.rule_set_id,"FALSE_POSITIVE",
            "PREDICTED_MECHANISM_NOT_OBSERVED_IN_COMPLETE_WINDOW",
        )

    if not inputs.direction_consistent:
        return OutcomeMappingDecision(
            inputs.case_id,inputs.rule_set_id,"INVALIDATED",
            "MECHANISM_OBSERVED_BUT_DIRECTION_INCONSISTENT",
        )

    if inputs.explicit_horizon_defined and inputs.horizon_met is False:
        return OutcomeMappingDecision(
            inputs.case_id,inputs.rule_set_id,"RIGHT_MECHANISM_WRONG_TIMING",
            "MECHANISM_AND_DIRECTION_REALIZED_OUTSIDE_EXPLICIT_HORIZON",
        )

    if (
        inputs.explicit_numeric_target_defined
        and inputs.target_met is True
        and inputs.causal_attribution_clean
    ):
        return OutcomeMappingDecision(
            inputs.case_id,inputs.rule_set_id,"TRUE_POSITIVE",
            "EXPLICIT_TARGET_MET_WITH_CLEAN_ATTRIBUTION",
        )

    return OutcomeMappingDecision(
        inputs.case_id,inputs.rule_set_id,"PARTIAL_REALIZATION",
        "MECHANISM_DIRECTION_SUPPORTED_BUT_FULL_TARGET_OR_CAUSAL_PROOF_ABSENT",
    )


def _dt(value: str, label: str) -> datetime:
    try:
        ts=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc:
        raise OutcomeMappingError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise OutcomeMappingError(f"{label}: timezone-aware timestamp required")
    return ts


def load_outcome_mapping_bundle(
    path: str | Path,
) -> tuple[datetime, tuple[OutcomeMappingInputs,...]]:
    raw=json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version")!="1.0":
        raise OutcomeMappingError("unsupported outcome mapping schema")
    if raw.get("rule_set_id")!=POSITIVE_CONSTRAINT_RULESET_V1:
        raise OutcomeMappingError("unsupported outcome mapping rule set")
    declared_at=_dt(raw["declared_at"],"declared_at")

    records=[]
    seen=set()
    for item in raw.get("cases",[]):
        record=OutcomeMappingInputs(
            case_id=item["case_id"],
            rule_set_id=raw["rule_set_id"],
            mechanism_observed=item["mechanism_observed"],
            direction_consistent=item["direction_consistent"],
            explicit_numeric_target_defined=item["explicit_numeric_target_defined"],
            target_met=item.get("target_met"),
            explicit_horizon_defined=item["explicit_horizon_defined"],
            horizon_met=item.get("horizon_met"),
            causal_attribution_clean=item["causal_attribution_clean"],
            outcome_observation_complete=item["outcome_observation_complete"],
            contradiction_open=item["contradiction_open"],
            evidence_source_ids=tuple(item["evidence_source_ids"]),
            rationale=item["rationale"],
        )
        record.validate()
        if record.case_id in seen:
            raise OutcomeMappingError(f"duplicate case_id {record.case_id}")
        seen.add(record.case_id)
        records.append(record)
    if not records:
        raise OutcomeMappingError("outcome mapping bundle is empty")
    return declared_at,tuple(records)
