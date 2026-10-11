from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
import re

SOURCE_PRIORITY = {
    "federal_register": 100,
    "ofac": 100,
    "utility_regulator": 100,
    "sec_edgar": 95,
    "official_agency": 95,
    "official_port": 90,
    "company_ir": 80,
    "customs_manifest": 70,
    "secondary_report": 40,
    "rumor": 10,
}
SOURCE_EVIDENCE = {
    "federal_register":"A1","ofac":"A1","utility_regulator":"A1","sec_edgar":"A1",
    "official_agency":"A1","official_port":"A1","company_ir":"A2",
    "customs_manifest":"B1","secondary_report":"B2","rumor":"C",
}

def _iso_date(value: str) -> str:
    value=(value or "").strip()
    if "T" in value:
        if value.endswith("Z"):
            return value
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return value + "Z"
        return value if parsed.utcoffset() is not None else value + "Z"
    return f"{value}T00:00:00Z"

def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+","-",value.strip()).strip("-").upper()

def _meta(source_class: str, external_record_id: str, adapter: str) -> Dict[str,Any]:
    return {
        "source_class":source_class,
        "source_priority":SOURCE_PRIORITY[source_class],
        "adapter_name":adapter,
        "external_record_id":external_record_id,
    }

@dataclass
class BISFederalRegisterAdapter:
    name: str="BISFederalRegisterAdapter"
    source_class: str="federal_register"
    def adapt(self,r):
        doc=str(r["document_number"]).strip(); published=_iso_date(r["publication_date"])
        out={
            "headline":r["title"],"event_key":f"BIS-FR:{doc}",
            "event_type":r.get("event_type","export_control_rule"),"target":r["target"],
            "occurred_at":published,"known_at":published,
            "effective_at":_iso_date(r.get("effective_date") or r["publication_date"]),
            "source_published_at":published,"captured_at":r["captured_at"],
            "source_id":f"BIS_FR_{_slug(doc)}","source_url":r["url"],
            "evidence_class":SOURCE_EVIDENCE[self.source_class],
            "severity":float(r.get("severity",0.7)),"jurisdiction":r.get("jurisdiction"),
            "commodity":r.get("commodity"),"record_status":"confirmed",
            "details":{"federal_register_document":doc,"agency":"Bureau of Industry and Security"},
        }
        out.update(_meta(self.source_class,doc,self.name)); return out

@dataclass
class OFACRecentActionAdapter:
    name: str="OFACRecentActionAdapter"
    source_class: str="ofac"
    def adapt(self,r):
        rid=str(r.get("action_id") or _slug(r["title"]+"-"+r["date"])); date=_iso_date(r["date"])
        out={
            "headline":r["title"],"event_key":f"OFAC:{rid}",
            "event_type":r.get("event_type","sanctions_action"),"target":r["target"],
            "occurred_at":date,"known_at":date,"effective_at":_iso_date(r.get("effective_date") or r["date"]),
            "source_published_at":date,"captured_at":r["captured_at"],
            "source_id":f"OFAC_{_slug(rid)}","source_url":r["url"],
            "evidence_class":"A1","severity":float(r.get("severity",0.65)),
            "jurisdiction":r.get("jurisdiction"),"record_status":"confirmed",
            "details":{"category":r.get("category"),"program":r.get("program"),"action_id":rid},
        }
        out.update(_meta(self.source_class,rid,self.name)); return out

@dataclass
class SECEdgarAdapter:
    name: str="SECEdgarAdapter"
    source_class: str="sec_edgar"
    def adapt(self,r):
        acc=str(r["accession_number"]).replace("-",""); date=_iso_date(r["filing_date"])
        out={
            "headline":f'{r["company"]} filed {r["form"]}',"event_key":f"SEC:{acc}",
            "event_type":r.get("event_type","sec_filing"),"target":r["target"],
            "occurred_at":date,"known_at":date,"effective_at":date,"source_published_at":date,
            "captured_at":r["captured_at"],"source_id":f"SEC_{acc}","source_url":r["url"],
            "evidence_class":"A1","severity":float(r.get("severity",0.35)),
            "jurisdiction":r.get("jurisdiction","United States"),"record_status":"confirmed",
            "details":{"cik":str(r["cik"]),"accession_number":r["accession_number"],"form":r["form"],
                       "report_date":r.get("report_date"),"primary_document":r.get("primary_document")},
        }
        out.update(_meta(self.source_class,acc,self.name)); return out

@dataclass
class PortAuthorityAdapter:
    name: str="PortAuthorityAdapter"
    source_class: str="official_port"
    def adapt(self,r):
        rid=str(r.get("release_id") or _slug(r["title"]+"-"+r["date"])); date=_iso_date(r["date"])
        state=str(r.get("operational_state","update")).lower()
        typ={"disruption":"port_disruption","closure":"port_closure","delay":"port_delay","congestion":"port_congestion"}.get(state,"port_operational_update")
        out={
            "headline":r["title"],"event_key":f"PORT:{rid}","event_type":typ,"target":r["target"],
            "occurred_at":_iso_date(r.get("occurred_date") or r["date"]),"known_at":date,
            "effective_at":_iso_date(r.get("effective_date") or r.get("occurred_date") or r["date"]),
            "source_published_at":date,"captured_at":r["captured_at"],"source_id":f"PORT_{_slug(rid)}",
            "source_url":r["url"],"evidence_class":"A1","severity":float(r.get("severity",0.7)),
            "jurisdiction":r.get("jurisdiction","United States"),"record_status":"confirmed",
            "details":{"port_name":r.get("port_name"),"operational_state":state},
        }
        out.update(_meta(self.source_class,rid,self.name)); return out

@dataclass
class UtilityRegulatorAdapter:
    name: str="UtilityRegulatorAdapter"
    source_class: str="utility_regulator"
    def adapt(self,r):
        docket=str(r["docket"]); order=str(r.get("order_id") or r.get("document_id") or r["order_date"])
        ext=f"{docket}:{order}"; date=_iso_date(r["order_date"])
        out={
            "headline":r["title"],"event_key":f"UTILITY:{ext}",
            "event_type":r.get("event_type","utility_regulatory_order"),"target":r["target"],
            "occurred_at":date,"known_at":date,"effective_at":_iso_date(r.get("effective_date") or r["order_date"]),
            "source_published_at":date,"captured_at":r["captured_at"],
            "source_id":f"REG_{_slug(docket)}_{_slug(order)}","source_url":r["url"],
            "evidence_class":"A1","severity":float(r.get("severity",0.45)),
            "jurisdiction":r.get("jurisdiction"),"record_status":"confirmed",
            "details":{"regulator":r["regulator"],"docket":docket,"order_id":order,"service":r.get("service")},
        }
        out.update(_meta(self.source_class,ext,self.name)); return out

@dataclass
class CustomsManifestAdapter:
    name: str="CustomsManifestAdapter"
    source_class: str="customs_manifest"
    def adapt(self,r):
        bol=str(r["bill_of_lading"]); date=_iso_date(r["ship_date"])
        out={
            "headline":f'Observed shipment {r.get("origin","")} -> {r.get("destination","")} for {r.get("consignee","")}',
            "event_key":f"MANIFEST:{bol}","event_type":"logistics_observation","target":r["target"],
            "occurred_at":date,"known_at":_iso_date(r.get("known_date") or r["ship_date"]),"effective_at":date,
            "source_published_at":None,"captured_at":r["captured_at"],"source_id":f"MANIFEST_{_slug(bol)}",
            "source_url":r.get("url"),"evidence_class":"B1","severity":float(r.get("severity",0.15)),
            "jurisdiction":r.get("jurisdiction"),"record_status":"confirmed",
            "details":{"bill_of_lading":bol,"origin":r.get("origin"),"destination":r.get("destination"),
                       "consignee":r.get("consignee"),"cargo":r.get("cargo"),"carrier":r.get("carrier")},
        }
        out.update(_meta(self.source_class,bol,self.name)); return out

@dataclass
class CompanyIRAdapter:
    name: str="CompanyIRAdapter"
    source_class: str="company_ir"
    def adapt(self,r):
        rid=str(r.get("release_id") or _slug(r["company"]+"-"+r["title"]+"-"+r["date"])); date=_iso_date(r["date"])
        out={
            "headline":r["title"],"event_key":f"IR:{rid}","event_type":r.get("event_type","company_ir_update"),
            "target":r["target"],"occurred_at":date,"known_at":date,
            "effective_at":_iso_date(r.get("effective_date") or r["date"]),"source_published_at":date,
            "captured_at":r["captured_at"],"source_id":f"IR_{_slug(rid)}","source_url":r["url"],
            "evidence_class":"A2","severity":float(r.get("severity",0.4)),"jurisdiction":r.get("jurisdiction"),
            "record_status":"confirmed","details":{"company":r["company"],"release_id":rid},
        }
        out.update(_meta(self.source_class,rid,self.name)); return out

ADAPTERS={
    "bis_federal_register":BISFederalRegisterAdapter(),
    "ofac_recent_action":OFACRecentActionAdapter(),
    "sec_edgar":SECEdgarAdapter(),
    "port_authority":PortAuthorityAdapter(),
    "utility_regulator":UtilityRegulatorAdapter(),
    "customs_manifest":CustomsManifestAdapter(),
    "company_ir":CompanyIRAdapter(),
}
