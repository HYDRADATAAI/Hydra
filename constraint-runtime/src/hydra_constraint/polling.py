from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import csv
import hashlib
import io
import json
import math
from collections.abc import Mapping
import os
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from .adapters import ADAPTERS

RETRYABLE={429,500,502,503,504}
DEFAULT_MAX_RESPONSE_BYTES=2_000_000

class ResponseTooLargeError(ValueError):
    def __init__(self, max_bytes, status=None):
        self.max_bytes=max_bytes
        self.status=status
        super().__init__(f"response exceeds max_bytes={max_bytes}")

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
    def delay(self,attempt:int,retry_after:Optional[str]=None)->float:
        if retry_after:
            try:
                return min(self.cap_seconds,max(0.0,float(retry_after)))
            except Exception:
                pass
        return min(self.cap_seconds,self.base_seconds*(2**max(0,attempt-1)))

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

def _require_https_url(url):
    try:
        parsed=urlsplit(url)
        hostname=parsed.hostname
        parsed.port
    except (AttributeError,TypeError,ValueError) as exc:
        raise ValueError("poll source URL must be a valid HTTPS URL") from exc
    if (
        parsed.scheme.casefold()!="https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("poll source URL must be an HTTPS URL with a hostname and no credentials")

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def _read_bounded(stream,max_bytes,status):
    body=bytearray()
    while len(body)<=max_bytes:
        chunk=stream.read(max_bytes+1-len(body))
        if not chunk:
            break
        body.extend(chunk)
    if len(body)>max_bytes:
        raise ResponseTooLargeError(max_bytes,status)
    return bytes(body)

class UrllibTransport:
    def __init__(self,max_bytes=DEFAULT_MAX_RESPONSE_BYTES):
        if not isinstance(max_bytes,int) or isinstance(max_bytes,bool) or max_bytes<=0:
            raise ValueError("max_bytes must be a positive integer")
        self.max_bytes=max_bytes

    def fetch(self,url,headers=None,timeout=20,max_bytes=None):
        if max_bytes is None:
            max_bytes=self.max_bytes
        if not isinstance(max_bytes,int) or isinstance(max_bytes,bool) or max_bytes<=0:
            raise ValueError("max_bytes must be a positive integer")
        _require_https_url(url)
        req=urllib.request.Request(url,headers=headers or {},method="GET")
        opener=urllib.request.build_opener(_NoRedirectHandler())
        try:
            with opener.open(req,timeout=timeout) as response:
                status=int(response.status)
                body=_read_bounded(response,max_bytes,status)
                return HttpResponse(
                    url,status,{key.lower():value for key,value in response.headers.items()},
                    body,utc_now(),
                )
        except urllib.error.HTTPError as error:
            with error:
                status=int(error.code)
                body=_read_bounded(error,max_bytes,status)
                headers={key.lower():value for key,value in (error.headers.items() if error.headers else [])}
                return HttpResponse(url,status,headers,body,utc_now())

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
    def __init__(self,durable,cursors,archive,transport,sleeper=None,max_response_bytes=None):
        self.durable=durable; self.cursors=cursors; self.archive=archive
        self.transport=transport; self.sleeper=sleeper or time
        if max_response_bytes is None:
            max_response_bytes=(
                transport.max_bytes
                if isinstance(transport,UrllibTransport)
                else DEFAULT_MAX_RESPONSE_BYTES
            )
        if not isinstance(max_response_bytes,int) or isinstance(max_response_bytes,bool) or max_response_bytes<=0:
            raise ValueError("max_response_bytes must be a positive integer")
        self.max_response_bytes=max_response_bytes

    def _uses_builtin_urllib_transport(self):
        return (
            isinstance(self.transport,UrllibTransport)
            and type(self.transport).fetch is UrllibTransport.fetch
        )

    def validate_live_spec(self,spec):
        sec_selector=(
            str(spec.adapter).casefold()=="sec_edgar"
            or str(spec.source_class).casefold()=="sec_edgar"
            or str(spec.parser).casefold()=="sec_json"
        )
        try:
            parsed_url=urlsplit(spec.url)
            host=(parsed_url.hostname or "").encode("idna").decode("ascii").casefold().rstrip(".")
        except (AttributeError,TypeError,ValueError) as exc:
            if sec_selector:
                raise ValueError("SEC polling requires a valid HTTPS SEC URL") from exc
            return
        is_sec_host=host=="sec.gov" or host.endswith(".sec.gov")
        if not sec_selector and not is_sec_host:
            return
        if (spec.adapter,spec.source_class,spec.parser)!=("sec_edgar","sec_edgar","sec_json"):
            raise ValueError("SEC polling requires matching sec_edgar adapter/source_class and sec_json parser")
        try:
            port=parsed_url.port
        except ValueError as exc:
            raise ValueError("SEC polling requires a valid HTTPS SEC URL") from exc
        if (parsed_url.scheme.casefold()!="https" or not is_sec_host or port not in (None,443)
                or parsed_url.username is not None or parsed_url.password is not None):
            raise ValueError("SEC polling requires an HTTPS URL on sec.gov or a subdomain")
        if not isinstance(spec.headers,Mapping):
            raise ValueError("SEC polling headers must be a mapping with one User-Agent")
        user_agent_values=[
            value for key,value in spec.headers.items()
            if str(key).casefold()=="user-agent"
        ]
        if len(user_agent_values)!=1 or not isinstance(user_agent_values[0],str):
            raise ValueError("SEC live polling requires exactly one User-Agent header")
        user_agent=user_agent_values[0].strip()
        if not user_agent or "REPLACE_" in user_agent.upper() or "\r" in user_agent or "\n" in user_agent:
            raise ValueError("SEC live polling requires a non-empty, non-placeholder User-Agent")
        if isinstance(spec.max_rps,bool):
            raise ValueError("SEC max_rps must be a finite number above zero and at or below 10")
        try:
            max_rps=float(spec.max_rps)
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError("SEC max_rps must be a finite number above zero and at or below 10") from exc
        if not math.isfinite(max_rps) or max_rps<=0 or max_rps>10:
            raise ValueError("SEC max_rps must be a finite number above zero and at or below 10")

    def poll(self,spec,cursor_value=None):
        self.validate_live_spec(spec)
        if self._uses_builtin_urllib_transport():
            _require_https_url(spec.url)
        before=self.cursors.adapter(spec.name).get("cursor")
        statuses=[]; hashes=[]; delays=[]; response=None; error=None
        for attempt in range(1,spec.backoff.max_attempts+1):
            try:
                if self._uses_builtin_urllib_transport():
                    response=self.transport.fetch(
                        spec.url,spec.headers,max_bytes=self.max_response_bytes,
                    )
                else:
                    response=self.transport.fetch(spec.url,spec.headers)
            except ResponseTooLargeError as exc:
                if exc.status is not None:
                    statuses.append(exc.status)
                error=str(exc); response=None
                break
            except Exception as exc:
                error=str(exc); response=None
                if attempt<spec.backoff.max_attempts:
                    delay=spec.backoff.delay(attempt); delays.append(delay); self.sleeper.sleep(delay); continue
                break
            if len(response.body)>self.max_response_bytes:
                statuses.append(response.status)
                error=str(ResponseTooLargeError(self.max_response_bytes,response.status))
                response=None
                break
            statuses.append(response.status)
            hashes.append(self.archive.archive(spec.name,response,attempt))
            if response.status==200:
                break
            if response.status not in RETRYABLE or attempt>=spec.backoff.max_attempts:
                error=f"HTTP {response.status}"; break
            delay=spec.backoff.delay(attempt,response.headers.get("retry-after"))
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
