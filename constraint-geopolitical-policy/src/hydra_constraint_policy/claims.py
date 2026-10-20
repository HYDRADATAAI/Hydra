from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from pathlib import Path


class ClaimEvidenceError(ValueError):
    pass


class ClaimStance(str,Enum):
    SUPPORTING="supporting"
    OPPOSING="opposing"
    NEUTRAL="neutral"


class ClaimState(str,Enum):
    NO_AVAILABLE_EVIDENCE="NO_AVAILABLE_EVIDENCE"
    SUPPORT_ONLY="SUPPORT_ONLY"
    OPPOSITION_ONLY="OPPOSITION_ONLY"
    CONTESTED="CONTESTED"
    NEUTRAL_ONLY="NEUTRAL_ONLY"


class RevisionRelation(str,Enum):
    MODIFIES="MODIFIES"
    SUPERSEDES="SUPERSEDES"
    RETRACTS="RETRACTS"
    CLARIFIES="CLARIFIES"


@dataclass(frozen=True)
class ClaimEvidence:
    evidence_id: str
    document_id: str
    known_at: datetime
    stance: ClaimStance
    attributed_to: str
    statement: str

    def validate(self) -> None:
        if not all((self.evidence_id,self.document_id,self.attributed_to,self.statement)):
            raise ClaimEvidenceError("claim evidence identity, attribution and statement required")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ClaimEvidenceError(f"{self.evidence_id}: timezone-aware known_at required")


@dataclass(frozen=True)
class ContestedClaim:
    claim_id: str
    proposition: str
    evidence: tuple[ClaimEvidence,...]

    def validate(self) -> None:
        if not self.claim_id or not self.proposition:
            raise ClaimEvidenceError("claim identity/proposition required")
        if not self.evidence:
            raise ClaimEvidenceError(f"{self.claim_id}: evidence required")
        ids=set()
        for item in self.evidence:
            item.validate()
            if item.evidence_id in ids:
                raise ClaimEvidenceError(f"{self.claim_id}: duplicate evidence_id {item.evidence_id}")
            ids.add(item.evidence_id)


@dataclass(frozen=True)
class HistoricalRevision:
    revision_id: str
    prior_document_id: str
    revision_document_id: str
    known_at: datetime
    relation: RevisionRelation
    scope: str

    def validate(self) -> None:
        if not all((self.revision_id,self.prior_document_id,self.revision_document_id,self.scope)):
            raise ClaimEvidenceError("revision identity/documents/scope required")
        if self.prior_document_id==self.revision_document_id:
            raise ClaimEvidenceError(f"{self.revision_id}: revision cannot reference the same document")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ClaimEvidenceError(f"{self.revision_id}: timezone-aware known_at required")


def claim_state_as_of(claim: ContestedClaim, as_of: datetime) -> ClaimState:
    claim.validate()
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ClaimEvidenceError("as_of must be timezone-aware")
    available=[e for e in claim.evidence if e.known_at<=as_of]
    if not available:
        return ClaimState.NO_AVAILABLE_EVIDENCE
    stances={e.stance for e in available}
    if ClaimStance.SUPPORTING in stances and ClaimStance.OPPOSING in stances:
        return ClaimState.CONTESTED
    if ClaimStance.SUPPORTING in stances:
        return ClaimState.SUPPORT_ONLY
    if ClaimStance.OPPOSING in stances:
        return ClaimState.OPPOSITION_ONLY
    return ClaimState.NEUTRAL_ONLY


def available_claim_evidence(claim: ContestedClaim, as_of: datetime) -> tuple[ClaimEvidence,...]:
    claim.validate()
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ClaimEvidenceError("as_of must be timezone-aware")
    return tuple(sorted(
        (e for e in claim.evidence if e.known_at<=as_of),
        key=lambda e:(e.known_at,e.evidence_id),
    ))


def revisions_as_of(revisions: tuple[HistoricalRevision,...], as_of: datetime) -> tuple[HistoricalRevision,...]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ClaimEvidenceError("as_of must be timezone-aware")
    ids=set()
    out=[]
    for revision in revisions:
        revision.validate()
        if revision.revision_id in ids:
            raise ClaimEvidenceError(f"duplicate revision_id {revision.revision_id}")
        ids.add(revision.revision_id)
        if revision.known_at<=as_of:
            out.append(revision)
    return tuple(sorted(out,key=lambda r:(r.known_at,r.revision_id)))


def _parse_dt(value: str, label: str) -> datetime:
    try:
        ts=datetime.fromisoformat(value.replace("Z","+00:00"))
    except Exception as exc:
        raise ClaimEvidenceError(f"{label}: invalid timestamp") from exc
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ClaimEvidenceError(f"{label}: timezone-aware timestamp required")
    return ts


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ClaimEvidenceError(f"{label}: object required")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ClaimEvidenceError(f"{label}: array required")
    return value


def _required_value(item: dict[str, object], field: str, label: str) -> object:
    if field not in item:
        raise ClaimEvidenceError(f"{label}.{field}: value required")
    return item[field]


def _required_text(item: dict[str, object], field: str, label: str) -> str:
    value = _required_value(item, field, label)
    if not isinstance(value, str) or not value:
        raise ClaimEvidenceError(f"{label}.{field}: non-empty string required")
    return value


def load_claim_revision_bundle(
    path: str | Path,
) -> tuple[tuple[ContestedClaim,...],tuple[HistoricalRevision,...]]:
    raw = _require_object(
        json.loads(Path(path).read_text(encoding="utf-8")),
        "$",
    )
    claims = []
    for claim_index, value in enumerate(_require_array(raw.get("claims", []), "$.claims")):
        label = f"$.claims[{claim_index}]"
        item = _require_object(value, label)
        evidence = []
        for evidence_index, evidence_value in enumerate(
            _require_array(item.get("evidence", []), f"{label}.evidence")
        ):
            evidence_label = f"{label}.evidence[{evidence_index}]"
            evidence_item = _require_object(evidence_value, evidence_label)
            try:
                stance = ClaimStance(_required_value(evidence_item, "stance", evidence_label))
            except (TypeError, ValueError) as exc:
                raise ClaimEvidenceError(f"{evidence_label}.stance: invalid value") from exc
            evidence.append(ClaimEvidence(
                evidence_id=_required_text(evidence_item, "evidence_id", evidence_label),
                document_id=_required_text(evidence_item, "document_id", evidence_label),
                known_at=_parse_dt(
                    _required_text(evidence_item, "known_at", evidence_label),
                    f"{evidence_label}.known_at",
                ),
                stance=stance,
                attributed_to=_required_text(evidence_item, "attributed_to", evidence_label),
                statement=_required_text(evidence_item, "statement", evidence_label),
            ))
        claim = ContestedClaim(
            claim_id=_required_text(item, "claim_id", label),
            proposition=_required_text(item, "proposition", label),
            evidence=tuple(evidence),
        )
        claim.validate()
        claims.append(claim)

    revisions = []
    for revision_index, value in enumerate(
        _require_array(raw.get("revisions", []), "$.revisions")
    ):
        label = f"$.revisions[{revision_index}]"
        item = _require_object(value, label)
        try:
            relation = RevisionRelation(_required_value(item, "relation", label))
        except (TypeError, ValueError) as exc:
            raise ClaimEvidenceError(f"{label}.relation: invalid value") from exc
        revision = HistoricalRevision(
            revision_id=_required_text(item, "revision_id", label),
            prior_document_id=_required_text(item, "prior_document_id", label),
            revision_document_id=_required_text(item, "revision_document_id", label),
            known_at=_parse_dt(
                _required_text(item, "known_at", label),
                f"{label}.known_at",
            ),
            relation=relation,
            scope=_required_text(item, "scope", label),
        )
        revision.validate()
        revisions.append(revision)

    claim_ids=[c.claim_id for c in claims]
    revision_ids=[r.revision_id for r in revisions]
    if len(claim_ids)!=len(set(claim_ids)):
        raise ClaimEvidenceError("duplicate claim_id")
    if len(revision_ids)!=len(set(revision_ids)):
        raise ClaimEvidenceError("duplicate revision_id")
    return tuple(claims),tuple(revisions)
