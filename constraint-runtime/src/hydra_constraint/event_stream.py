from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
import copy
import hashlib
import json
import re

from .runtime import ConstraintRuntime, Event

VALID_EVIDENCE = {"A1","A2","B1","B2","C","D","OPEN"}
EVENT_EVIDENCE_RANK = {"A1":7,"A2":6,"B1":5,"B2":4,"C":3,"D":2,"OPEN":1}
EVENT_FACTOR = {"A1":1.00,"A2":0.92,"B1":0.70,"B2":0.62,"C":0.0,"D":0.0,"OPEN":0.0}
EVENT_STATE = {"A1":"CONFIRMED","A2":"CONFIRMED","B1":"CANDIDATE","B2":"CANDIDATE","C":"BLOCKED","D":"DEFERRED","OPEN":"BLOCKED"}
COUNTRY_ALIASES = {
    "us":"unitedstates","usa":"unitedstates","unitedstatesofamerica":"unitedstates","unitedstates":"unitedstates",
    "southkorea":"southkorea","republicofkorea":"southkorea","korea":"southkorea",
    "taiwan":"taiwan","china":"china","canada":"canada","mexico":"mexico","global":"global",
}

class IngestError(ValueError):
    pass

def _dt(value: Optional[str], field_name: str, *, required: bool=False) -> Optional[datetime]:
    if value in (None,""):
        if required:
            raise IngestError(f"missing required datetime: {field_name}")
        return None
    s=str(value).strip()
    if s.endswith("Z"):
        s=s[:-1]+"+00:00"
    try:
        out=datetime.fromisoformat(s)
    except ValueError as exc:
        raise IngestError(f"invalid datetime {field_name}: {value}") from exc
    if out.tzinfo is None:
        out=out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)

def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def _norm_text(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+","",(value or "").lower())

def _country_key(value: Optional[str]) -> str:
    x=_norm_text(value)
    return COUNTRY_ALIASES.get(x,x)

def _stable_hash(*parts: str, length: int=24) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:length]

def _raw_hash(record: Dict[str,Any]) -> str:
    return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")).hexdigest()

@dataclass
class CanonicalEvent:
    event_id: str
    fingerprint: str
    event_key: Optional[str]
    event_type: str
    target_node_id: str
    headline: str
    occurred_at: str
    known_at: str
    effective_at: str
    source_published_at: Optional[str]
    captured_at: str
    evidence_class: str
    severity: float
    jurisdiction: Optional[str]=None
    commodity: Optional[str]=None
    record_status: str="confirmed"
    source_ids: List[str]=field(default_factory=list)
    source_urls: List[str]=field(default_factory=list)
    raw_hashes: List[str]=field(default_factory=list)
    details: Dict[str,Any]=field(default_factory=dict)
    ingest_notes: List[str]=field(default_factory=list)

    def to_dict(self) -> Dict[str,Any]:
        return asdict(self)

@dataclass
class IngestDecision:
    disposition: str
    fingerprint: Optional[str]
    event_id: Optional[str]
    reason: str
    canonical_event: Optional[CanonicalEvent]=None

    def to_dict(self) -> Dict[str,Any]:
        x=asdict(self)
        if self.canonical_event:
            x["canonical_event"]=self.canonical_event.to_dict()
        return x

class TargetResolver:
    def __init__(self,graph: Dict[str,Any],aliases: Optional[Dict[str,str]]=None):
        self.nodes={n["node_id"]:n for n in graph["nodes"]}
        self.name_index: Dict[str,List[str]]={}
        for node in graph["nodes"]:
            candidates=[node["name"],node["node_id"]]
            md=node.get("metadata",{})
            for key in ("asset_name","company","location","provider_or_node","material","country"):
                if md.get(key):
                    candidates.append(str(md[key]))
            if md.get("company") and md.get("location"):
                candidates.append(f'{md["company"]} {md["location"]}')
            for candidate in candidates:
                k=_norm_text(candidate)
                if k:
                    self.name_index.setdefault(k,[]).append(node["node_id"])
        self.aliases={_norm_text(k):v for k,v in (aliases or {}).items()}

    def resolve(self,value: str) -> str:
        if value in self.nodes:
            return value
        key=_norm_text(value)
        if key in self.aliases:
            node_id=self.aliases[key]
            if node_id not in self.nodes:
                raise IngestError(f"alias resolves to missing node: {value} -> {node_id}")
            return node_id
        ids=sorted(set(self.name_index.get(key,[])))
        if len(ids)==1:
            return ids[0]
        if len(ids)>1:
            raise IngestError(f"ambiguous target: {value}")
        raise IngestError(f"unresolved target: {value}")

class EventNormalizer:
    def __init__(self,graph: Dict[str,Any],aliases: Optional[Dict[str,str]]=None):
        self.nodes={n["node_id"]:n for n in graph["nodes"]}
        self.resolver=TargetResolver(graph,aliases=aliases)

    def normalize(self,raw: Dict[str,Any]) -> CanonicalEvent:
        event_type=str(raw.get("event_type") or "").strip()
        if not event_type:
            raise IngestError("missing event_type")
        target_raw=raw.get("target_node_id") or raw.get("target")
        if not target_raw:
            raise IngestError("missing target_node_id/target")
        target_node_id=self.resolver.resolve(str(target_raw))
        node=self.nodes[target_node_id]
        evidence=str(raw.get("evidence_class") or "OPEN").upper().strip()
        if evidence not in VALID_EVIDENCE:
            raise IngestError(f"invalid evidence_class: {evidence}")
        record_status=str(raw.get("record_status") or "confirmed").lower().strip()
        notes=[]
        if record_status in {"rumor","unverified","speculation"} and EVENT_EVIDENCE_RANK[evidence]>EVENT_EVIDENCE_RANK["C"]:
            evidence="C"
            notes.append("rumor/unverified status caps event evidence at C")
        if record_status in {"retracted","false"}:
            evidence="OPEN"
            notes.append("retracted/false record is blocked")
        severity=float(raw.get("severity",0.5))
        if not 0<=severity<=1:
            raise IngestError("severity must be between 0 and 1")
        captured=_dt(raw.get("captured_at"),"captured_at",required=True)
        published=_dt(raw.get("source_published_at"),"source_published_at")
        known=_dt(raw.get("known_at"),"known_at")
        if known is None:
            known=published or captured
            notes.append("known_at derived from source_published_at/captured_at")
        occurred=_dt(raw.get("occurred_at"),"occurred_at")
        if occurred is None:
            occurred=known
            notes.append("occurred_at derived from known_at")
        effective=_dt(raw.get("effective_at"),"effective_at")
        if effective is None:
            effective=occurred
            notes.append("effective_at derived from occurred_at")
        jurisdiction=raw.get("jurisdiction")
        node_jurisdiction=node.get("jurisdiction")
        cross_border=bool((raw.get("details") or {}).get("cross_border"))
        if jurisdiction and node_jurisdiction and _country_key(node_jurisdiction) not in {"","global"}:
            if _country_key(jurisdiction)!=_country_key(node_jurisdiction) and not cross_border:
                raise IngestError(f"jurisdiction mismatch: event={jurisdiction} target={node_jurisdiction}")
        event_key=str(raw.get("event_key") or "").strip() or None
        commodity=str(raw.get("commodity") or "").strip() or None
        if event_key:
            identity=f"KEY|{event_type}|{target_node_id}|{_norm_text(event_key)}"
        else:
            eff_minute=effective.replace(second=0,microsecond=0)
            identity=f"TIME|{event_type}|{target_node_id}|{_iso(eff_minute)}|{_norm_text(commodity)}"
        fingerprint=_stable_hash(identity,length=32)
        event_id="EVT_"+fingerprint[:20].upper()
        source_id=str(raw.get("source_id") or "").strip()
        source_url=str(raw.get("source_url") or "").strip()
        return CanonicalEvent(
            event_id=event_id,fingerprint=fingerprint,event_key=event_key,event_type=event_type,target_node_id=target_node_id,
            headline=str(raw.get("headline") or "").strip(),occurred_at=_iso(occurred),known_at=_iso(known),effective_at=_iso(effective),
            source_published_at=_iso(published),captured_at=_iso(captured),evidence_class=evidence,severity=severity,
            jurisdiction=str(jurisdiction).strip() if jurisdiction else None,commodity=commodity,record_status=record_status,
            source_ids=[source_id] if source_id else [],source_urls=[source_url] if source_url else [],
            raw_hashes=[_raw_hash(raw)],details=copy.deepcopy(raw.get("details") or {}),ingest_notes=notes,
        )

class EventStore:
    def __init__(self,normalizer: EventNormalizer):
        self.normalizer=normalizer
        self.events: Dict[str,CanonicalEvent]={}

    def ingest_one(self,raw: Dict[str,Any]) -> IngestDecision:
        try:
            incoming=self.normalizer.normalize(raw)
        except IngestError as exc:
            return IngestDecision("REJECTED",None,None,str(exc),None)
        existing=self.events.get(incoming.fingerprint)
        if existing is None:
            self.events[incoming.fingerprint]=incoming
            return IngestDecision("ACCEPTED_NEW",incoming.fingerprint,incoming.event_id,"new canonical event",incoming)
        if existing.effective_at!=incoming.effective_at:
            existing.ingest_notes.append(f"CONFLICT effective_at existing={existing.effective_at} incoming={incoming.effective_at}")
            existing.record_status="conflict"
            return IngestDecision("CONFLICT",existing.fingerprint,existing.event_id,"same event identity has conflicting effective_at; manual/stronger-source resolution required",existing)
        existing.source_ids=sorted(set(existing.source_ids)|set(incoming.source_ids))
        existing.source_urls=sorted(set(existing.source_urls)|set(incoming.source_urls))
        existing.raw_hashes=sorted(set(existing.raw_hashes)|set(incoming.raw_hashes))
        if _dt(incoming.known_at,"known_at",required=True)<_dt(existing.known_at,"known_at",required=True):
            existing.known_at=incoming.known_at
            existing.ingest_notes.append("known_at moved earlier from duplicate source")
        if EVENT_EVIDENCE_RANK[incoming.evidence_class]>EVENT_EVIDENCE_RANK[existing.evidence_class]:
            existing.evidence_class=incoming.evidence_class
            existing.ingest_notes.append("evidence upgraded by duplicate source")
        existing.severity=max(existing.severity,incoming.severity)
        return IngestDecision("DUPLICATE_MERGED",existing.fingerprint,existing.event_id,"same event fingerprint; sources merged without creating a second canonical event",existing)

    def ingest_many(self,records: Iterable[Dict[str,Any]]) -> List[IngestDecision]:
        return [self.ingest_one(r) for r in records]

    def canonical_events(self) -> List[CanonicalEvent]:
        return sorted(self.events.values(),key=lambda x:(x.known_at,x.effective_at,x.event_id))

    def to_jsonable(self) -> List[Dict[str,Any]]:
        return [e.to_dict() for e in self.canonical_events()]

class ReplayHarness:
    def __init__(self,runtime: ConstraintRuntime):
        self.runtime=runtime

    def evaluate(self,event: CanonicalEvent,as_of: str,max_hops: int=8) -> Dict[str,Any]:
        as_of_dt=_dt(as_of,"as_of",required=True)
        known_dt=_dt(event.known_at,"known_at",required=True)
        effective_dt=_dt(event.effective_at,"effective_at",required=True)
        base={
            "event_id":event.event_id,"fingerprint":event.fingerprint,"event_type":event.event_type,
            "target_node_id":event.target_node_id,"known_at":event.known_at,"effective_at":event.effective_at,
            "as_of":_iso(as_of_dt),"event_evidence_class":event.evidence_class,"event_record_status":event.record_status,
            "no_auto_trading_signal":True,
        }
        if event.record_status in {"conflict","retracted","false"}:
            return {**base,"replay_state":"BLOCKED","reason":"event record is conflicted/retracted/false","exposures":[],"runtime_result":None}
        if known_dt>as_of_dt:
            return {**base,"replay_state":"NOT_KNOWN","reason":"event was not yet known as of replay time","exposures":[],"runtime_result":None}
        if effective_dt>as_of_dt:
            return {**base,"replay_state":"PENDING_EFFECTIVE","reason":"event is known but not yet physically/economically effective","exposures":[],"runtime_result":None}
        event_state=EVENT_STATE[event.evidence_class]
        if event_state=="BLOCKED":
            return {**base,"replay_state":"BLOCKED","reason":"event-level evidence cannot propagate as fact","exposures":[],"runtime_result":None}
        if event_state=="DEFERRED":
            return {**base,"replay_state":"DEFERRED","reason":"event-level evidence is deferred","exposures":[],"runtime_result":None}
        result=self.runtime.evaluate_event(Event(
            event_id=event.event_id,event_type=event.event_type,target_node_id=event.target_node_id,
            occurred_at=event.effective_at,known_at=event.known_at,severity=event.severity,
            commodity=event.commodity,jurisdiction=event.jurisdiction,details=event.details,
        ),max_hops=max_hops).to_dict()
        exposures=copy.deepcopy(result["exposures"])
        if event_state=="CANDIDATE":
            factor=EVENT_FACTOR[event.evidence_class]
            for x in exposures:
                if x["state"]=="CONFIRMED":
                    x["state"]="CANDIDATE"
                x["physical_severity_score"]=round(x["physical_severity_score"]*factor,2)
                x.setdefault("reasons",[]).insert(0,f"event evidence {event.evidence_class} caps downstream state at CANDIDATE")
            replay_state="CANDIDATE"
        else:
            replay_state="CONFIRMED"
        return {**base,"replay_state":replay_state,"reason":"event and graph passed replay gates","exposures":exposures,"runtime_result":result}

    def replay_stream(self,events: Iterable[CanonicalEvent],as_of: str,*,since_known_at: Optional[str]=None,max_hops: int=8) -> List[Dict[str,Any]]:
        cutoff=_dt(since_known_at,"since_known_at") if since_known_at else None
        selected=[]
        for event in events:
            known=_dt(event.known_at,"known_at",required=True)
            if cutoff and known<=cutoff:
                continue
            selected.append(event)
        selected.sort(key=lambda x:(x.known_at,x.effective_at,x.event_id))
        return [self.evaluate(e,as_of=as_of,max_hops=max_hops) for e in selected]
