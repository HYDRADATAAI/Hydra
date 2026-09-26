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


def load_claim_revision_bundle(
    path: str | Path,
) -> tuple[tuple[ContestedClaim,...],tuple[HistoricalRevision,...]]:
    raw=json.loads(Path(path).read_text(encoding="utf-8"))
    claims=[]
    for item in raw.get("claims",[]):
        evidence=[]
        for e in item.get("evidence",[]):
            evidence.append(ClaimEvidence(
                evidence_id=e["evidence_id"],
                document_id=e["document_id"],
                known_at=_parse_dt(e["known_at"],f"{e['evidence_id']}.known_at"),
                stance=ClaimStance(e["stance"]),
                attributed_to=e["attributed_to"],
                statement=e["statement"],
            ))
        claim=ContestedClaim(
            claim_id=item["claim_id"],
            proposition=item["proposition"],
            evidence=tuple(evidence),
        )
        claim.validate()
        claims.append(claim)

    revisions=[]
    for item in raw.get("revisions",[]):
        revision=HistoricalRevision(
            revision_id=item["revision_id"],
            prior_document_id=item["prior_document_id"],
            revision_document_id=item["revision_document_id"],
            known_at=_parse_dt(item["known_at"],f"{item['revision_id']}.known_at"),
            relation=RevisionRelation(item["relation"]),
            scope=item["scope"],
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
