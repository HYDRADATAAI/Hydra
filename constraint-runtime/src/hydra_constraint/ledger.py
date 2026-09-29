from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import copy
import hashlib
import json

from .event_stream import CanonicalEvent, EventNormalizer, IngestError
from .adapters import SOURCE_PRIORITY

VALID_ACTIONS={"CREATE","MERGE_SOURCE","CORRECT","SUPERSEDE","RETRACT","QUARANTINE"}

def _dt(value: str) -> datetime:
    s=value[:-1]+"+00:00" if value.endswith("Z") else value
    out=datetime.fromisoformat(s)
    if out.tzinfo is None:
        out=out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)

def _canon(value: Any) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),default=str)

def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()

@dataclass
class LedgerEntry:
    sequence:int
    action:str
    event_id:str
    fingerprint:str
    event_version:int
    recorded_at:str
    source_class:str
    source_priority:int
    source_id:Optional[str]
    external_record_id:Optional[str]
    supersedes_sequence:Optional[int]
    prior_entry_hash:str
    payload_hash:str
    entry_hash:str
    reason:str
    payload:Dict[str,Any]

    def to_dict(self)->Dict[str,Any]:
        return asdict(self)

class AppendOnlyEventLedger:
    def __init__(self,normalizer: EventNormalizer):
        self.normalizer=normalizer
        self.entries:List[LedgerEntry]=[]
        self._active:Dict[str,Dict[str,Any]]={}
        self._versions:Dict[str,int]={}
        self._last_sequence:Dict[str,int]={}

    @property
    def tip_hash(self)->str:
        return self.entries[-1].entry_hash if self.entries else "GENESIS"

    def _append(self,action,event,raw,reason,supersedes_sequence=None):
        if action not in VALID_ACTIONS:
            raise ValueError(action)
        source_class=str(raw.get("source_class") or "secondary_report")
        priority=int(raw.get("source_priority",SOURCE_PRIORITY.get(source_class,0)))
        version=self._versions.get(event.fingerprint,0)+1
        seq=len(self.entries)+1
        payload=event.to_dict()
        payload_hash=_sha(payload)
        unsigned={
            "sequence":seq,"action":action,"event_id":event.event_id,"fingerprint":event.fingerprint,
            "event_version":version,"recorded_at":raw["captured_at"],"source_class":source_class,
            "source_priority":priority,"source_id":raw.get("source_id"),
            "external_record_id":raw.get("external_record_id"),
            "supersedes_sequence":supersedes_sequence,"prior_entry_hash":self.tip_hash,
            "payload_hash":payload_hash,"reason":reason,
        }
        entry_hash=_sha(unsigned)
        entry=LedgerEntry(
            sequence=seq,action=action,event_id=event.event_id,fingerprint=event.fingerprint,
            event_version=version,recorded_at=raw["captured_at"],source_class=source_class,
            source_priority=priority,source_id=raw.get("source_id"),
            external_record_id=raw.get("external_record_id"),
            supersedes_sequence=supersedes_sequence,prior_entry_hash=self.tip_hash,
            payload_hash=payload_hash,entry_hash=entry_hash,reason=reason,payload=payload,
        )
        self.entries.append(entry)
        self._versions[event.fingerprint]=version
        self._last_sequence[event.fingerprint]=seq
        return entry

    def ingest_adapted(self,raw:Dict[str,Any])->LedgerEntry:
        try:
            incoming=self.normalizer.normalize(raw)
        except IngestError as exc:
            payload={
                "event_id":"QUARANTINE_"+_sha(raw)[:16].upper(),
                "fingerprint":"QUARANTINE_"+_sha(raw)[:24],
                "event_key":raw.get("event_key"),"event_type":raw.get("event_type","unknown"),
                "target_node_id":str(raw.get("target_node_id") or raw.get("target") or ""),
                "headline":str(raw.get("headline") or ""),
                "occurred_at":raw.get("occurred_at") or raw["captured_at"],
                "known_at":raw.get("known_at") or raw["captured_at"],
                "effective_at":raw.get("effective_at") or raw.get("occurred_at") or raw["captured_at"],
                "source_published_at":raw.get("source_published_at"),"captured_at":raw["captured_at"],
                "evidence_class":"OPEN","severity":float(raw.get("severity",0)),
                "jurisdiction":raw.get("jurisdiction"),"commodity":raw.get("commodity"),
                "record_status":"quarantined",
                "source_ids":[raw.get("source_id")] if raw.get("source_id") else [],
                "source_urls":[raw.get("source_url")] if raw.get("source_url") else [],
                "raw_hashes":[_sha(raw)],"details":raw.get("details") or {},"ingest_notes":[str(exc)],
            }
            return self._append("QUARANTINE",CanonicalEvent(**payload),raw,f"ingest rejected: {exc}")

        fp=incoming.fingerprint
        current=self._active.get(fp)
        priority=int(raw.get("source_priority",0))
        if current is None:
            entry=self._append("CREATE",incoming,raw,"new canonical event")
            self._active[fp]={"event":incoming,"priority":priority,"sequence":entry.sequence,"retracted":False}
            return entry

        existing=current["event"]
        current_priority=int(current["priority"])
        last_seq=int(current["sequence"])
        same_effective=incoming.effective_at==existing.effective_at
        same_type=incoming.event_type==existing.event_type
        same_target=incoming.target_node_id==existing.target_node_id

        if same_effective and same_type and same_target:
            merged=copy.deepcopy(existing)
            merged.source_ids=sorted(set(existing.source_ids)|set(incoming.source_ids))
            merged.source_urls=sorted(set(existing.source_urls)|set(incoming.source_urls))
            merged.raw_hashes=sorted(set(existing.raw_hashes)|set(incoming.raw_hashes))
            if _dt(incoming.known_at)<_dt(existing.known_at):
                merged.known_at=incoming.known_at
            if priority>current_priority:
                merged.evidence_class=incoming.evidence_class
            merged.severity=max(existing.severity,incoming.severity)
            entry=self._append("MERGE_SOURCE",merged,raw,"duplicate identity; merged provenance",last_seq)
            self._active[fp]={"event":merged,"priority":max(priority,current_priority),"sequence":entry.sequence,"retracted":False}
            return entry

        if priority>=current_priority:
            corrected=copy.deepcopy(incoming)
            corrected.source_ids=sorted(set(existing.source_ids)|set(incoming.source_ids))
            corrected.source_urls=sorted(set(existing.source_urls)|set(incoming.source_urls))
            corrected.raw_hashes=sorted(set(existing.raw_hashes)|set(incoming.raw_hashes))
            corrected.known_at=min(existing.known_at,incoming.known_at)
            action="CORRECT" if incoming.event_type==existing.event_type and incoming.target_node_id==existing.target_node_id else "SUPERSEDE"
            entry=self._append(action,corrected,raw,f"source priority {priority} >= active {current_priority}; event facts updated",last_seq)
            self._active[fp]={"event":corrected,"priority":priority,"sequence":entry.sequence,"retracted":False}
            return entry

        conflict=copy.deepcopy(incoming)
        conflict.record_status="conflict"
        conflict.ingest_notes.append(f"lower-priority conflict rejected: incoming={priority} active={current_priority}")
        return self._append("QUARANTINE",conflict,raw,"lower-authority source cannot overwrite active event facts",last_seq)

    def retract(self,fingerprint: str,*,recorded_at: str,source_class: str,source_id: str,external_record_id: str,reason: str)->LedgerEntry:
        if fingerprint not in self._active:
            raise KeyError(fingerprint)
        current=self._active[fingerprint]
        event=copy.deepcopy(current["event"])
        event.record_status="retracted"
        event.evidence_class="OPEN"
        raw={"captured_at":recorded_at,"source_class":source_class,"source_priority":SOURCE_PRIORITY[source_class],
             "source_id":source_id,"external_record_id":external_record_id}
        entry=self._append("RETRACT",event,raw,reason,current["sequence"])
        self._active[fingerprint]={"event":event,"priority":SOURCE_PRIORITY[source_class],"sequence":entry.sequence,"retracted":True}
        return entry

    def active_events(self,as_of_recorded_at:Optional[str]=None)->List[Dict[str,Any]]:
        entries=self.entries
        if as_of_recorded_at:
            cutoff=_dt(as_of_recorded_at)
            entries=[e for e in entries if _dt(e.recorded_at)<=cutoff]
        state={}
        for entry in entries:
            if entry.action!="QUARANTINE":
                state[entry.fingerprint]=entry
        out=[]
        for _,entry in sorted(state.items(),key=lambda kv:(kv[1].payload.get("known_at",""),kv[0])):
            if entry.action=="RETRACT" or entry.payload.get("record_status")=="retracted":
                continue
            out.append(copy.deepcopy(entry.payload))
        return out

    def event_history(self,fingerprint:str)->List[Dict[str,Any]]:
        return [e.to_dict() for e in self.entries if e.fingerprint==fingerprint]

    def verify_chain(self)->Dict[str,Any]:
        prev="GENESIS"
        issues=[]
        for entry in self.entries:
            if entry.prior_entry_hash!=prev:
                issues.append({"sequence":entry.sequence,"code":"BROKEN_PRIOR_HASH"})
            if _sha(entry.payload)!=entry.payload_hash:
                issues.append({"sequence":entry.sequence,"code":"PAYLOAD_HASH_MISMATCH"})
            unsigned={
                "sequence":entry.sequence,"action":entry.action,"event_id":entry.event_id,"fingerprint":entry.fingerprint,
                "event_version":entry.event_version,"recorded_at":entry.recorded_at,"source_class":entry.source_class,
                "source_priority":entry.source_priority,"source_id":entry.source_id,"external_record_id":entry.external_record_id,
                "supersedes_sequence":entry.supersedes_sequence,"prior_entry_hash":entry.prior_entry_hash,
                "payload_hash":entry.payload_hash,"reason":entry.reason,
            }
            if _sha(unsigned)!=entry.entry_hash:
                issues.append({"sequence":entry.sequence,"code":"ENTRY_HASH_MISMATCH"})
            prev=entry.entry_hash
        return {"status":"PASS" if not issues else "FAIL","entries":len(self.entries),"tip_hash":self.tip_hash,"issues":issues}

    def to_jsonable(self)->List[Dict[str,Any]]:
        return [e.to_dict() for e in self.entries]
