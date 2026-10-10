from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request

from .adapters import ADAPTERS

RETRYABLE={429,500,502,503,504}
_RFC850_DATE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), [0-9]{2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(?P<year>[0-9]{2}) "
    r"[0-9]{2}:[0-9]{2}:[0-9]{2} GMT",
    re.ASCII,
)
_HTTP_DATE = re.compile(
    r"(?:"
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), [0-9]{2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [0-9]{4} "
    r"[0-9]{2}:[0-9]{2}:[0-9]{2} GMT|"
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), [0-9]{2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-[0-9]{2} "
    r"[0-9]{2}:[0-9]{2}:[0-9]{2} GMT|"
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (?: [1-9]|0[1-9]|[12][0-9]|3[01]) "
    r"[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4}"
    r")",
    re.ASCII,
)

def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def _atomic_json(path:Path,obj:Any):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(obj,f,indent=2,sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

@dataclass
class HttpResponse:
    url:str
    status:int
    headers:Dict[str,str]
    body:bytes
    captured_at:str

@dataclass
class BackoffPolicy:
    max_attempts:int=4
    base_seconds:float=1.0
    cap_seconds:float=30.0
    def delay(
        self,
        attempt: int,
        retry_after: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> float:
        if retry_after:
            delay_seconds = retry_after.strip()
            if delay_seconds.isascii() and delay_seconds.isdigit():
                numeric_retry_after = Decimal(delay_seconds)
                if numeric_retry_after >= Decimal(str(self.cap_seconds)):
                    return self.cap_seconds
                return float(numeric_retry_after)
            try:
                date_value = retry_after.strip()
                if not _HTTP_DATE.fullmatch(date_value):
                    raise ValueError("invalid HTTP-date")
                current = now or datetime.now(timezone.utc)
                if current.tzinfo is None:
                    current = current.replace(tzinfo=timezone.utc)
                rfc850_match = _RFC850_DATE.fullmatch(date_value)
                leap_second = ":60 " in date_value
                if leap_second:
                    date_value = date_value.replace(":60 ", ":59 ", 1)
                retry_at = parsedate_to_datetime(date_value)
                if leap_second:
                    retry_at += timedelta(seconds=1)
                if rfc850_match:
                    year = current.year // 100 * 100 + int(rfc850_match.group("year"))
                    retry_at = retry_at.replace(year=year)
                    try:
                        fifty_years_ahead = current.replace(year=current.year + 50)
                    except ValueError:
                        fifty_years_ahead = current.replace(
                            year=current.year + 50,
                            day=28,
                        )
                    if retry_at > fifty_years_ahead:
                        retry_at = retry_at.replace(year=year - 100)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return min(
                    self.cap_seconds,
                    max(0.0, (retry_at - current).total_seconds()),
                )
            except (TypeError, ValueError, OverflowError):
                pass
        return min(self.cap_seconds, self.base_seconds * (2 ** max(0, attempt - 1)))

@dataclass
class PollSpec:
    name:str
    adapter:str
    source_class:str
    url:str
    parser:str
    cadence_minutes:int
    stale_after_minutes:int
    target:Optional[str]=None
    jurisdiction:Optional[str]=None
    severity:float=0.4
    max_rps:float=1.0
    headers:Dict[str,str]=field(default_factory=dict)
    parser_config:Dict[str,Any]=field(default_factory=dict)
    backoff:BackoffPolicy=field(default_factory=BackoffPolicy)

    @classmethod
    def from_dict(cls,x):
        x=dict(x)
        x["backoff"]=BackoffPolicy(**x.get("backoff",{}))
        return cls(**x)

class FixtureTransport:
    def __init__(self,responses):
        self.responses={k:list(v) for k,v in responses.items()}
        self.calls={}
    def fetch(self,url,headers=None,timeout=20):
        seq=self.responses[url]
        i=self.calls.get(url,0)
        self.calls[url]=i+1
        return seq[min(i,len(seq)-1)]

class UrllibTransport:
    def fetch(self,url,headers=None,timeout=20):
        req=urllib.request.Request(url,headers=headers or {},method="GET")
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return HttpResponse(url,int(r.status),{k.lower():v for k,v in r.headers.items()},r.read(),utc_now())
        except urllib.error.HTTPError as e:
            return HttpResponse(url,int(e.code),{k.lower():v for k,v in (e.headers.items() if e.headers else [])},e.read(),utc_now())

class RecordingSleeper:
    def __init__(self):
        self.delays=[]
    def sleep(self,seconds):
        self.delays.append(seconds)

class RawArchive:
    def __init__(self,root):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
    def archive(self,source,response,attempt):
        sha=hashlib.sha256(response.body).hexdigest()
        d=self.root/source/response.captured_at[:10].replace("-","")
        d.mkdir(parents=True,exist_ok=True)
        body=d/f"{sha}.bin"
        meta=d/f"{sha}.json"
        if not body.exists():
            body.write_bytes(response.body)
        _atomic_json(meta,{
            "source":source,"url":response.url,"status":response.status,"captured_at":response.captured_at,
            "attempt":attempt,"sha256":sha,"bytes":len(response.body),"headers":response.headers,
            "body_file":str(body.relative_to(self.root)).replace("\\","/"),
        })
        return sha

def parse_bis_csv(body,spec,captured):
    import re
    out=[]
    for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig"))):
        title=row.get("Title","")
        target=None
        for rule in spec.parser_config.get("keyword_rules",[]):
            if re.search(rule["pattern"],title,re.I):
                target=rule["target"]; break
        if not target:
            continue
        out.append({
            "document_number":row.get("FR Citation") or row.get("Document Number"),
            "title":title,"publication_date":row["Publication Date"],
            "effective_date":row.get("Effective Date") or row["Publication Date"],
            "target":target,"commodity":spec.parser_config.get("commodity"),
            "jurisdiction":spec.jurisdiction,"severity":spec.severity,
            "url":row.get("URL") or spec.url,"captured_at":captured,
            "event_type":"export_control_rule",
        })
    return out

def parse_json_records(body,spec,captured):
    x=json.loads(body.decode("utf-8"))
    out=[]
    for row in x["records"]:
        r=dict(row); r["captured_at"]=captured
        if spec.target and "target" not in r:
            r["target"]=spec.target
        if spec.jurisdiction and "jurisdiction" not in r:
            r["jurisdiction"]=spec.jurisdiction
        r.setdefault("severity",spec.severity)
        out.append(r)
    return out

def parse_sec_json(body,spec,captured):
    x=json.loads(body.decode("utf-8"))
    rec=x["filings"]["recent"]
    forms=set(spec.parser_config.get("forms",["8-K","10-Q","10-K","6-K"]))
    out=[]
    for i,acc in enumerate(rec["accessionNumber"]):
        if rec["form"][i] not in forms:
            continue
        out.append({
            "cik":str(x["cik"]),"accession_number":acc,"filing_date":rec["filingDate"][i],
            "report_date":rec["reportDate"][i],"form":rec["form"][i],
            "primary_document":rec["primaryDocument"][i],"company":x["name"],
            "target":spec.target,"jurisdiction":spec.jurisdiction,"severity":spec.severity,
            "url":spec.url,"captured_at":captured,
        })
    return out

PARSERS={"bis_csv":parse_bis_csv,"json_records":parse_json_records,"sec_json":parse_sec_json}

@dataclass
class PollReport:
    source:str
    status:str
    attempts:int
    http_statuses:List[int]
    raw_hashes:List[str]
    parsed_records:int
    appended:int
    skipped_seen:int
    quarantined:int
    cursor_before:Optional[str]
    cursor_after:Optional[str]
    captured_at:Optional[str]
    error:Optional[str]=None
    backoff_delays:List[float]=field(default_factory=list)
    def to_dict(self):
        return asdict(self)

class PollRunner:
    def __init__(self,durable,cursors,archive,transport,sleeper=None,clock=None,wall_clock=None):
        self.durable=durable; self.cursors=cursors; self.archive=archive
        self.transport=transport; self.sleeper=sleeper or time
        self.clock=clock or time.monotonic
        self.wall_clock=wall_clock or (lambda: datetime.now(timezone.utc))
        self._poll_lock=threading.Lock()
        self._last_request_at={}
        self._next_request_at={}

    @staticmethod
    def _request_interval(spec):
        if isinstance(spec.max_rps,bool) or not isinstance(spec.max_rps,(int,float)):
            raise ValueError("max_rps must be finite and greater than zero")
        try:
            rate=float(spec.max_rps)
        except (OverflowError,ValueError):
            raise ValueError("max_rps must be finite and greater than zero") from None
        if not math.isfinite(rate) or rate<=0:
            raise ValueError("max_rps must be finite and greater than zero")
        interval=1.0/rate
        if not math.isfinite(interval):
            raise ValueError("max_rps is too small to pace safely")
        return interval

    def _pace_request(self,spec,interval):
        last=self._last_request_at.get(spec.name)
        now=self.clock()
        rate_deadline=last+interval if last is not None else now
        deadline=max(rate_deadline,self._next_request_at.get(spec.name,now))
        remaining=deadline-now
        if remaining>0:
            self.sleeper.sleep(remaining)
        self._last_request_at[spec.name]=self.clock()

    def _defer_source(self,spec,delay):
        deadline=self.clock()+delay
        self._next_request_at[spec.name]=max(
            deadline,self._next_request_at.get(spec.name,deadline)
        )

    def validate_live_spec(self,spec):
        if spec.source_class=="sec_edgar":
            ua=spec.headers.get("User-Agent","")
            if not ua or "REPLACE_" in ua:
                raise ValueError("SEC live polling requires real User-Agent/contact")
            if spec.max_rps>10:
                raise ValueError("SEC max_rps exceeds fair-access ceiling")

    def poll(self,spec,cursor_value=None):
        interval=self._request_interval(spec)
        with self._poll_lock:
            return self._poll_locked(spec,cursor_value,interval)

    def _poll_locked(self,spec,cursor_value,interval):
        before=self.cursors.adapter(spec.name).get("cursor")
        statuses=[]; hashes=[]; delays=[]; response=None; error=None
        for attempt in range(1,spec.backoff.max_attempts+1):
            self._pace_request(spec,interval)
            try:
                response=self.transport.fetch(spec.url,spec.headers)
            except Exception as exc:
                error=str(exc); response=None
            if response is None:
                delay=spec.backoff.delay(attempt)
                self._defer_source(spec,delay)
                if attempt<spec.backoff.max_attempts:
                    delays.append(delay); self.sleeper.sleep(delay); continue
                break
            statuses.append(response.status)
            hashes.append(self.archive.archive(spec.name,response,attempt))
            if response.status==200:
                break
            if response.status not in RETRYABLE:
                error=f"HTTP {response.status}"; break
            delay=spec.backoff.delay(
                attempt,
                response.headers.get("retry-after"),
                now=self.wall_clock(),
            )
            self._defer_source(spec,delay)
            if attempt>=spec.backoff.max_attempts:
                error=f"HTTP {response.status}"; break
            delays.append(delay); self.sleeper.sleep(delay)

        if response is None or response.status!=200:
            self.cursors.mark_error(spec.name,polled_at=response.captured_at if response else utc_now(),error=error or "poll failed")
            return PollReport(spec.name,"FAILED",len(statuses),statuses,hashes,0,0,0,0,before,before,response.captured_at if response else None,error,delays)

        try:
            records=PARSERS[spec.parser](response.body,spec,response.captured_at)
        except Exception as exc:
            self.cursors.mark_error(spec.name,polled_at=response.captured_at,error=f"parse:{exc}")
            return PollReport(spec.name,"PARSE_FAILED",len(statuses),statuses,hashes,0,0,0,0,before,before,response.captured_at,str(exc),delays)

        appended=skipped=quarantined=0
        new_ids=[]
        try:
            for payload in records:
                raw=ADAPTERS[spec.adapter].adapt(payload)
                ext=raw.get("external_record_id")
                if self.cursors.has_seen(spec.name,ext):
                    skipped+=1; continue
                entry=self.durable.ingest_adapted(raw)
                appended+=1
                quarantined+=entry.action=="QUARANTINE"
                if ext:
                    new_ids.append(ext)
        except Exception as exc:
            self.cursors.mark_error(spec.name,polled_at=response.captured_at,error=f"append:{exc}")
            return PollReport(spec.name,"APPEND_FAILED",len(statuses),statuses,hashes,len(records),appended,skipped,quarantined,before,before,response.captured_at,str(exc),delays)

        state=self.cursors.adapter(spec.name)
        ids=state.get("seen_external_ids",[])
        for ext in new_ids:
            ids=[x for x in ids if x!=ext]+[ext]
        state["seen_external_ids"]=ids[-self.cursors.max_seen:]
        if new_ids:
            state["last_seen_external_record_id"]=new_ids[-1]
        state["cursor"]=cursor_value or response.headers.get("etag") or response.captured_at
        state["last_polled_at"]=response.captured_at
        state["last_success_at"]=response.captured_at
        state["last_error"]=None
        _atomic_json(self.cursors.path,self.cursors.state)
        return PollReport(spec.name,"PASS",len(statuses),statuses,hashes,len(records),appended,skipped,quarantined,before,state["cursor"],response.captured_at,None,delays)

class FreshnessMonitor:
    @staticmethod
    def evaluate(specs,cursors,as_of):
        now=datetime.fromisoformat(as_of.replace("Z","+00:00"))
        out=[]
        for spec in specs:
            state=cursors.adapter(spec.name)
            last=state.get("last_success_at")
            if not last:
                health="NEVER_SUCCESS"; age=None
            else:
                age=(now-datetime.fromisoformat(last.replace("Z","+00:00"))).total_seconds()/60
                health="HEALTHY" if age<=spec.stale_after_minutes else ("STALE" if age<=spec.stale_after_minutes*3 else "OUTAGE_OR_STALE")
            out.append({
                "source":spec.name,"health":health,"age_minutes":None if age is None else round(age,2),
                "last_success_at":last,"stale_after_minutes":spec.stale_after_minutes,
                "last_error":state.get("last_error"),"cursor":state.get("cursor"),
            })
        return out
