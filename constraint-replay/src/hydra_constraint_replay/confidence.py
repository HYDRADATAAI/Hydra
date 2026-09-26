from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any


class ConfidenceEvidenceError(ValueError):
    pass


class ConfidenceSemantics(str, Enum):
    NUMERIC_PROBABILITY = "NUMERIC_PROBABILITY"
    NUMERIC_PROBABILITY_RANGE = "NUMERIC_PROBABILITY_RANGE"
    PREDECLARED_ORDINAL_MAPPING = "PREDECLARED_ORDINAL_MAPPING"
    QUALITATIVE_EXPECTATION = "QUALITATIVE_EXPECTATION"
    QUALITATIVE_RISK = "QUALITATIVE_RISK"
    OPERATIONAL_COMMITMENT = "OPERATIONAL_COMMITMENT"
    TARGET_OR_OBJECTIVE = "TARGET_OR_OBJECTIVE"
    NONE = "NONE"


ADMISSIBLE_NUMERIC_SEMANTICS = {
    ConfidenceSemantics.NUMERIC_PROBABILITY,
    ConfidenceSemantics.NUMERIC_PROBABILITY_RANGE,
    ConfidenceSemantics.PREDECLARED_ORDINAL_MAPPING,
}


@dataclass(frozen=True)
class ConfidenceEvidence:
    evidence_id: str
    case_id: str
    source_id: str
    known_at: datetime
    semantics: ConfidenceSemantics
    statement: str
    numeric_value: float | None = None
    numeric_low: float | None = None
    numeric_high: float | None = None
    ordinal_label: str | None = None
    mapping_id: str | None = None
    notes: str = ""

    def validate(self) -> None:
        if not all((self.evidence_id,self.case_id,self.source_id,self.statement)):
            raise ConfidenceEvidenceError("confidence evidence identity/source/statement required")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ConfidenceEvidenceError(f"{self.evidence_id}: timezone-aware known_at required")

        if self.semantics == ConfidenceSemantics.NUMERIC_PROBABILITY:
            if self.numeric_value is None:
                raise ConfidenceEvidenceError(f"{self.evidence_id}: numeric probability requires value")
            if not 0 <= self.numeric_value <= 1:
                raise ConfidenceEvidenceError(f"{self.evidence_id}: probability outside [0,1]")
            if any(x is not None for x in (self.numeric_low,self.numeric_high,self.ordinal_label,self.mapping_id)):
                raise ConfidenceEvidenceError(f"{self.evidence_id}: incompatible fields for numeric probability")

        elif self.semantics == ConfidenceSemantics.NUMERIC_PROBABILITY_RANGE:
            if self.numeric_low is None or self.numeric_high is None:
                raise ConfidenceEvidenceError(f"{self.evidence_id}: numeric range requires low/high")
            if not 0 <= self.numeric_low <= self.numeric_high <= 1:
                raise ConfidenceEvidenceError(f"{self.evidence_id}: probability range outside [0,1]")
            if self.numeric_value is not None:
                raise ConfidenceEvidenceError(f"{self.evidence_id}: range cannot also carry scalar probability")

        elif self.semantics == ConfidenceSemantics.PREDECLARED_ORDINAL_MAPPING:
            if not self.ordinal_label or not self.mapping_id:
                raise ConfidenceEvidenceError(f"{self.evidence_id}: ordinal confidence requires label and mapping_id")
            if self.numeric_value is not None or self.numeric_low is not None or self.numeric_high is not None:
                raise ConfidenceEvidenceError(f"{self.evidence_id}: ordinal mapping cannot embed ad hoc numeric values")

        else:
            if any(x is not None for x in (self.numeric_value,self.numeric_low,self.numeric_high,self.ordinal_label,self.mapping_id)):
                raise ConfidenceEvidenceError(
                    f"{self.evidence_id}: non-probabilistic semantics cannot carry probability fields"
                )


@dataclass(frozen=True)
class OrdinalConfidenceMapping:
    mapping_id: str
    declared_at: datetime
    source_id: str
    values: tuple[tuple[str,float], ...]

    def validate(self) -> None:
        if not self.mapping_id or not self.source_id or not self.values:
            raise ConfidenceEvidenceError("ordinal mapping identity/source/values required")
        if self.declared_at.tzinfo is None or self.declared_at.utcoffset() is None:
            raise ConfidenceEvidenceError(f"{self.mapping_id}: timezone-aware declared_at required")
        labels=set()
        for label,value in self.values:
            if not label or label in labels:
                raise ConfidenceEvidenceError(f"{self.mapping_id}: duplicate/empty ordinal label")
            labels.add(label)
            if not 0 <= value <= 1:
                raise ConfidenceEvidenceError(f"{self.mapping_id}: mapped value outside [0,1]")


def admissible_confidence_value(
    evidence: ConfidenceEvidence,
    mappings: dict[str, OrdinalConfidenceMapping] | None = None,
) -> float | None:
    evidence.validate()
    if evidence.semantics == ConfidenceSemantics.NUMERIC_PROBABILITY:
        return evidence.numeric_value
    if evidence.semantics == ConfidenceSemantics.NUMERIC_PROBABILITY_RANGE:
        assert evidence.numeric_low is not None and evidence.numeric_high is not None
        return (evidence.numeric_low + evidence.numeric_high) / 2.0
    if evidence.semantics == ConfidenceSemantics.PREDECLARED_ORDINAL_MAPPING:
        mappings=mappings or {}
        mapping=mappings.get(evidence.mapping_id or "")
        if mapping is None:
            raise ConfidenceEvidenceError(f"{evidence.evidence_id}: ordinal mapping not found")
        mapping.validate()
        if mapping.declared_at > evidence.known_at:
            raise ConfidenceEvidenceError(
                f"{evidence.evidence_id}: ordinal mapping declared after confidence evidence"
            )
        values=dict(mapping.values)
        if evidence.ordinal_label not in values:
            raise ConfidenceEvidenceError(
                f"{evidence.evidence_id}: ordinal label absent from mapping"
            )
        return values[evidence.ordinal_label]
    return None


def _dt(value: str, label: str) -> datetime:
    try:
        ts=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc:
        raise ConfidenceEvidenceError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ConfidenceEvidenceError(f"{label}: timezone-aware timestamp required")
    return ts


def load_confidence_audit(
    path: str | Path,
) -> tuple[tuple[ConfidenceEvidence,...], dict[str,OrdinalConfidenceMapping]]:
    raw=json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema_version")!="1.0":
        raise ConfidenceEvidenceError("unsupported confidence audit schema")

    mappings={}
    for item in raw.get("ordinal_mappings",[]):
        mapping=OrdinalConfidenceMapping(
            mapping_id=item["mapping_id"],
            declared_at=_dt(item["declared_at"],f"{item['mapping_id']}.declared_at"),
            source_id=item["source_id"],
            values=tuple((str(x["label"]),float(x["value"])) for x in item["values"]),
        )
        mapping.validate()
        if mapping.mapping_id in mappings:
            raise ConfidenceEvidenceError(f"duplicate mapping_id {mapping.mapping_id}")
        mappings[mapping.mapping_id]=mapping

    evidence=[]
    seen=set()
    for item in raw.get("evidence",[]):
        ev=ConfidenceEvidence(
            evidence_id=item["evidence_id"],
            case_id=item["case_id"],
            source_id=item["source_id"],
            known_at=_dt(item["known_at"],f"{item['evidence_id']}.known_at"),
            semantics=ConfidenceSemantics(item["semantics"]),
            statement=item["statement"],
            numeric_value=item.get("numeric_value"),
            numeric_low=item.get("numeric_low"),
            numeric_high=item.get("numeric_high"),
            ordinal_label=item.get("ordinal_label"),
            mapping_id=item.get("mapping_id"),
            notes=item.get("notes",""),
        )
        ev.validate()
        if ev.evidence_id in seen:
            raise ConfidenceEvidenceError(f"duplicate evidence_id {ev.evidence_id}")
        seen.add(ev.evidence_id)
        evidence.append(ev)

    if not evidence:
        raise ConfidenceEvidenceError("confidence audit evidence is empty")
    return tuple(evidence),mappings


def summarize_confidence_audit(
    evidence: tuple[ConfidenceEvidence,...],
    mappings: dict[str,OrdinalConfidenceMapping] | None = None,
) -> dict[str,int]:
    mappings=mappings or {}
    admissible=0
    blocked=0
    by_semantics={s.value:0 for s in ConfidenceSemantics}
    for ev in evidence:
        by_semantics[ev.semantics.value]+=1
        value=admissible_confidence_value(ev,mappings)
        if value is None:
            blocked+=1
        else:
            admissible+=1
    return {
        "evidence_count":len(evidence),
        "admissible_numeric_confidence_count":admissible,
        "nonprobabilistic_or_blocked_count":blocked,
        **{f"semantics_{k}":v for k,v in by_semantics.items()},
    }
