from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import copy
import hashlib
import json
import os
import tempfile

from .event_stream import CanonicalEvent, EventNormalizer, ReplayHarness
from .ledger import AppendOnlyEventLedger, LedgerEntry

def _canon(value: Any) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),default=str)

def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()

def _atomic_json_replace(path: Path,value: Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(value,f,indent=2,sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

class LedgerCorruptionError(RuntimeError):
    pass

class JsonlLedgerStore:
    def __init__(self,path:str|Path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)

    def append(self,entry:LedgerEntry|Dict[str,Any])->None:
        record=entry.to_dict() if hasattr(entry,"to_dict") else dict(entry)
        line=(_canon(record)+"\n").encode("utf-8")
        fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644)
        try:
            if os.write(fd,line)!=len(line):
                raise OSError("short ledger append")
            os.fsync(fd)
        finally:
            os.close(fd)

    def load_raw(self):
        if not self.path.exists():
            return []
        out=[]
        with self.path.open("rb") as f:
            for lineno,raw in enumerate(f,1):
                if not raw.endswith(b"\n"):
                    raise LedgerCorruptionError(f"truncated ledger line {lineno}")
                try:
                    out.append(json.loads(raw.decode("utf-8")))
                except Exception as exc:
                    raise LedgerCorruptionError(f"invalid JSON ledger line {lineno}") from exc
        return out

def _entry_from_dict(x):
    return LedgerEntry(
        sequence=int(x["sequence"]),action=x["action"],event_id=x["event_id"],fingerprint=x["fingerprint"],
        event_version=int(x["event_version"]),recorded_at=x["recorded_at"],source_class=x["source_class"],
        source_priority=int(x["source_priority"]),source_id=x.get("source_id"),
        external_record_id=x.get("external_record_id"),supersedes_sequence=x.get("supersedes_sequence"),
        prior_entry_hash=x["prior_entry_hash"],payload_hash=x["payload_hash"],entry_hash=x["entry_hash"],
        reason=x["reason"],payload=copy.deepcopy(x["payload"]),
    )

def hydrate_ledger(normalizer:EventNormalizer,raw_entries):
    ledger=AppendOnlyEventLedger(normalizer)
    for x in raw_entries:
        entry=_entry_from_dict(x)
        ledger.entries.append(entry)
        ledger._versions[entry.fingerprint]=max(ledger._versions.get(entry.fingerprint,0),entry.event_version)
        ledger._last_sequence[entry.fingerprint]=entry.sequence
        if entry.action!="QUARANTINE":
            event=CanonicalEvent(**copy.deepcopy(entry.payload))
            priority=entry.source_priority
            if entry.action=="MERGE_SOURCE" and entry.fingerprint in ledger._active:
                priority=max(priority,int(ledger._active[entry.fingerprint]["priority"]))
            ledger._active[entry.fingerprint]={
                "event":event,"priority":priority,"sequence":entry.sequence,
                "retracted":entry.action=="RETRACT" or event.record_status=="retracted",
            }
    return ledger

class CheckpointStore:
    def __init__(self,path:str|Path):
        self.path=Path(path)

    def save(self,ledger):
        checkpoint={
            "format":"HYDRA_CONSTRAINT_CHECKPOINT_V1","ledger_entries":len(ledger.entries),
            "ledger_tip_hash":ledger.tip_hash,"active_events":ledger.active_events(),
        }
        checkpoint["checkpoint_hash"]=_sha({k:v for k,v in checkpoint.items() if k!="checkpoint_hash"})
        _atomic_json_replace(self.path,checkpoint)
        return checkpoint

    def load(self):
        if not self.path.exists():
            return None
        data=json.loads(self.path.read_text(encoding="utf-8"))
        expected=_sha({k:v for k,v in data.items() if k!="checkpoint_hash"})
        if data.get("checkpoint_hash")!=expected:
            raise LedgerCorruptionError("checkpoint hash mismatch")
        return data

class CursorStore:
    def __init__(self,path:str|Path,max_seen:int=1000):
        self.path=Path(path); self.max_seen=max_seen
        self.state=json.loads(self.path.read_text()) if self.path.exists() else {"format":"HYDRA_CONSTRAINT_CURSOR_V1","adapters":{}}

    def adapter(self,name):
        return self.state["adapters"].setdefault(name,{
            "cursor":None,"last_seen_external_record_id":None,"last_polled_at":None,
            "last_success_at":None,"last_error":None,"seen_external_ids":[],
        })

    def has_seen(self,adapter,external_id):
        return bool(external_id) and external_id in set(self.adapter(adapter)["seen_external_ids"])

    def mark_success(self,adapter,*,external_id,cursor,polled_at,success_at):
        x=self.adapter(adapter)
        if external_id:
            ids=[i for i in x["seen_external_ids"] if i!=external_id]+[external_id]
            x["seen_external_ids"]=ids[-self.max_seen:]
            x["last_seen_external_record_id"]=external_id
        x["cursor"]=cursor; x["last_polled_at"]=polled_at; x["last_success_at"]=success_at; x["last_error"]=None
        _atomic_json_replace(self.path,self.state)

    def mark_error(self,adapter,*,polled_at,error):
        x=self.adapter(adapter); x["last_polled_at"]=polled_at; x["last_error"]=error
        _atomic_json_replace(self.path,self.state)

class DurableLedgerRuntime:
    def __init__(self,normalizer,ledger_path,checkpoint_path):
        self.normalizer=normalizer
        self.store=JsonlLedgerStore(ledger_path)
        self.checkpoints=CheckpointStore(checkpoint_path)
        self.ledger=AppendOnlyEventLedger(normalizer)

    def recover(self):
        ledger=hydrate_ledger(self.normalizer,self.store.load_raw())
        chain=ledger.verify_chain()
        if chain["status"]!="PASS":
            raise LedgerCorruptionError(f"ledger chain failed: {chain['issues']}")
        checkpoint=self.checkpoints.load()
        state="MISSING"
        if checkpoint:
            state="MATCH" if checkpoint["ledger_entries"]==len(ledger.entries) and checkpoint["ledger_tip_hash"]==ledger.tip_hash else "STALE_REBUILT_FROM_LEDGER"
        self.ledger=ledger
        self.checkpoints.save(ledger)
        return {"status":"PASS","ledger_entries":len(ledger.entries),"ledger_tip_hash":ledger.tip_hash,
                "chain_status":"PASS","checkpoint_state":state,"active_events":len(ledger.active_events())}

    def ingest_adapted(self,raw):
        entry=self.ledger.ingest_adapted(raw)
        self.store.append(entry)
        self.checkpoints.save(self.ledger)
        return entry

class PollCoordinator:
    def __init__(self,durable:DurableLedgerRuntime,cursors:CursorStore):
        self.durable=durable; self.cursors=cursors

    def ingest_if_new(self,adapter_name,raw,*,cursor,polled_at,success_at):
        ext=raw.get("external_record_id")
        if self.cursors.has_seen(adapter_name,ext):
            return {"status":"SKIPPED_SEEN","external_record_id":ext}
        entry=self.durable.ingest_adapted(raw)
        self.cursors.mark_success(adapter_name,external_id=ext,cursor=cursor,polled_at=polled_at,success_at=success_at)
        return {"status":"APPENDED","sequence":entry.sequence,"entry_hash":entry.entry_hash}

class GoldenReplayStore:
    def __init__(self,directory:str|Path):
        self.directory=Path(directory); self.directory.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def graph_hash(graph):
        return _sha(graph)

    @staticmethod
    def replay_hash(replay):
        return _sha(replay)

    def create(self,*,ledger,graph,harness:ReplayHarness,as_of):
        events=[CanonicalEvent(**x) for x in ledger.active_events(as_of)]
        replay=harness.replay_stream(events,as_of)
        graph_hash=self.graph_hash(graph)
        key=_sha({"ledger_tip":ledger.tip_hash,"graph_hash":graph_hash,"as_of":as_of})[:32]
        snap={"format":"HYDRA_CONSTRAINT_GOLDEN_REPLAY_V1","snapshot_key":key,"as_of":as_of,
              "ledger_tip_hash":ledger.tip_hash,"ledger_entries":len(ledger.entries),"graph_hash":graph_hash,
              "replay_hash":self.replay_hash(replay),"replay":replay}
        _atomic_json_replace(self.directory/f"{key}.json",snap)
        return snap

    def compare(self,snapshot,*,ledger,graph,harness):
        events=[CanonicalEvent(**x) for x in ledger.active_events(snapshot["as_of"])]
        replay=harness.replay_stream(events,snapshot["as_of"])
        current={"ledger_tip_hash":ledger.tip_hash,"ledger_entries":len(ledger.entries),
                 "graph_hash":self.graph_hash(graph),"replay_hash":self.replay_hash(replay)}
        mismatches={k:{"expected":snapshot[k],"actual":v} for k,v in current.items() if snapshot[k]!=v}
        return {"status":"PASS" if not mismatches else "FAIL","mismatches":mismatches,"snapshot_key":snapshot["snapshot_key"]}
