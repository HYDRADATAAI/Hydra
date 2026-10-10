from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List
import csv
import hashlib
import io
import json

from .runtime import unresolved_admission

PARSER_VERSIONS={"bis_csv":"1.0.0","json_records":"1.0.0","sec_json":"1.0.0"}

def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

@dataclass
class DriftResult:
    source:str
    parser:str
    parser_version:str
    status:str
    observed_signature:str
    expected_signature:str
    issues:List[str]
    def to_dict(self):
        return asdict(self)

class DriftGuard:
    def __init__(self,contracts:Dict[str,Any]):
        self.contracts=contracts

    def inspect(self,source,parser,body:bytes):
        c=self.contracts[source]; issues=[]; observed={}
        if parser=="bis_csv":
            reader=csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
            observed["headers"]=list(reader.fieldnames or [])
            missing=[x for x in c["required_headers"] if x not in observed["headers"]]
            if missing:
                issues.append("missing_headers:"+",".join(missing))
        elif parser=="sec_json":
            try:
                x=json.loads(body.decode("utf-8"))
            except Exception:
                x={}; issues.append("invalid_json")
            if not isinstance(x,dict):
                issues.append("invalid_root_type")
                x={}
            filings=x.get("filings",{})
            if not isinstance(filings,dict):
                issues.append("invalid_filings_type")
                recent={}
            else:
                recent=filings.get("recent",{})
                if not isinstance(recent,dict):
                    issues.append("invalid_recent_type")
                    recent={}
            observed["root_keys"]=sorted(x.keys())
            observed["recent_keys"]=sorted(recent.keys())
            for key in c["required_root_keys"]:
                if key not in x:
                    issues.append("missing_root:"+key)
            for key in c["required_recent_keys"]:
                if key not in recent:
                    issues.append("missing_recent:"+key)
        else:
            try:
                x=json.loads(body.decode("utf-8"))
            except Exception:
                x={}; issues.append("invalid_json")
            records=x.get("records") if isinstance(x,dict) else None
            observed["root_keys"]=sorted(x.keys()) if isinstance(x,dict) else []
            observed["record_keys"]=sorted(records[0].keys()) if isinstance(records,list) and records else []
            if not isinstance(records,list):
                issues.append("missing_records_array")
            for key in c.get("required_record_keys",[]):
                if not isinstance(records,list) or not records or key not in records[0]:
                    issues.append("missing_record:"+key)
        return DriftResult(source,parser,PARSER_VERSIONS[parser],"FROZEN" if issues else "PASS",_sha(observed),_sha(c),issues)

@dataclass
class FailureBudgetPolicy:
    warn_at:int=2
    freeze_at:int=3
    recover_successes:int=2

class FailureBudget:
    def __init__(self,policy:FailureBudgetPolicy=FailureBudgetPolicy()):
        self.policy=policy
        self.sources={}

    def update(self,source,success,reason=None):
        x=self.sources.setdefault(source,{"consecutive_failures":0,"consecutive_successes":0,"state":"HEALTHY","last_reason":None})
        if success:
            x["consecutive_successes"]+=1; x["consecutive_failures"]=0
            if x["state"]=="FROZEN" and x["consecutive_successes"]>=self.policy.recover_successes:
                x["state"]="HEALTHY"
            elif x["state"]!="FROZEN":
                x["state"]="HEALTHY"
        else:
            x["consecutive_failures"]+=1; x["consecutive_successes"]=0; x["last_reason"]=reason
            if x["consecutive_failures"]>=self.policy.freeze_at:
                x["state"]="FROZEN"
            elif x["consecutive_failures"]>=self.policy.warn_at:
                x["state"]="WARN"
        return dict(x)

class DeploymentGuard:
    @staticmethod
    def validate(config):
        issues=[]
        for name,s in config["sources"].items():
            if s.get("enabled"):
                if s.get("live_canary") is not True or s.get("read_only") is not True:
                    issues.append(f"{name}: only explicit read-only canaries may be enabled while admission is blocked")
                if name.startswith("sec") and ("REPLACE_" in s.get("user_agent","") or not s.get("user_agent")):
                    issues.append(f"{name}: SEC User-Agent/contact not configured")
        return {"status":"PASS" if not issues else "FAIL","issues":issues,
                "status_scope":"CONFIGURATION_ONLY","admission":unresolved_admission()}

class OperationsReport:
    @staticmethod
    def build(*,freshness,drift,failure_state,ledger_recovery,golden,deployment):
        drift_map={x["source"]:x for x in drift}; fresh_map={x["source"]:x for x in freshness}
        sources=sorted(set(fresh_map)|set(drift_map)|set(failure_state.get("sources",{})))
        rows=[]
        for source in sources:
            rows.append({
                "source":source,"freshness":fresh_map.get(source,{}).get("health","UNKNOWN"),
                "drift":drift_map.get(source,{}).get("status","UNKNOWN"),
                "failure_budget":failure_state.get("sources",{}).get(source,{}).get("state","UNKNOWN"),
                "last_success_at":fresh_map.get(source,{}).get("last_success_at"),
                "last_error":fresh_map.get(source,{}).get("last_error"),
            })
        overall="PASS"
        if ledger_recovery.get("status")!="PASS" or golden.get("status")!="PASS" or deployment.get("status")!="PASS":
            overall="FAIL"
        elif any(x["drift"]=="FROZEN" or x["failure_budget"]=="FROZEN" for x in rows):
            overall="DEGRADED"
        elif not rows or any(x["freshness"]!="HEALTHY" or x["drift"]!="PASS" or x["failure_budget"]!="HEALTHY" for x in rows):
            overall="WARN"
        return {"status":overall,"ledger_tip_hash":ledger_recovery.get("ledger_tip_hash"),
                "ledger_chain":ledger_recovery.get("chain_status"),"golden_replay":golden.get("status"),
                "deployment":deployment.get("status"),"sources":rows,
                "status_scope":"OPERATIONS_ONLY","admission":unresolved_admission()}
