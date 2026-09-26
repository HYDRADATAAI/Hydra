from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
