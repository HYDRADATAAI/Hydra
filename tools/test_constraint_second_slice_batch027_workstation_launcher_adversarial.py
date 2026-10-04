#!/usr/bin/env python3
"""Hostile matrix for Batch027 workstation launcher contract."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=ROOT/"tools/validate_constraint_second_slice_batch027_workstation_launcher.py"
BASE="docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1"
CONTRACT=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_SEMICONDUCTOR_WORKSTATION_EXECUTION_LAUNCHER_CONTRACT_V001_20260926.json"
STATUS=f"{BASE}/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_SEMICONDUCTOR_WORKSTATION_EXECUTION_LAUNCHER_STATUS_V001_20260926.json"
MASTER="docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH027_MASTER_STATUS_V001_20260926.json"
LAUNCHER="tools/Invoke-HydraConstraintSemiconductorBatch026PrivateT1.ps1"
PRIVATE_CAPTURE_LAUNCHER="tools/private/Invoke-HYDRAConstraintSemiconductorBatch026BrowserCapture_V001_20260927.ps1"
CAPTURE_RUNNER="tools/private/HYDRA_CONSTRAINT_T1_SEMICONDUCTOR_BATCH026_BROWSER_CAPTURE_V001_20260927.py"

def sandbox():
    root=Path(tempfile.mkdtemp(prefix="hydra-semi-b027-hostile-"))
    shutil.copytree(ROOT/"docs/constraint",root/"docs/constraint",dirs_exist_ok=True)
    shutil.copytree(ROOT/"tools",root/"tools",dirs_exist_ok=True)
    return root
def mutate_json(root,rel,fn):
    p=root/rel; d=json.loads(p.read_text(encoding="utf-8")); fn(d); p.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
def mutate_text(root,rel,fn):
    p=root/rel; p.write_text(fn(p.read_text(encoding="utf-8")),encoding="utf-8")
def run(root):
    env=dict(os.environ); env["HYDRA_REPO_ROOT"]=str(root)
    return subprocess.run([sys.executable,str(VALIDATOR)],cwd=ROOT,env=env,text=True,capture_output=True,check=False)
def expect(name,fn,frag):
    root=sandbox()
    try:
      b=run(root)
      if b.returncode: raise AssertionError(f"{name}: baseline failed\n{b.stdout}\n{b.stderr}")
      fn(root); r=run(root)
      if r.returncode==0: raise AssertionError(f"{name}: hostile mutation passed")
      out=r.stdout+r.stderr
      if frag not in out: raise AssertionError(f"{name}: expected {frag!r}\n{out}")
      print(f"PASS :: {name} :: {frag}")
    finally: shutil.rmtree(root,ignore_errors=True)

def main():
    cases=[
      ("mode_removed",lambda r:mutate_json(r,CONTRACT,lambda d:d["modes"].pop()),"launcher mode set/order drifted"),
      ("network_guarantee_removed",lambda r:mutate_json(r,CONTRACT,lambda d:d.__setitem__("guarantees",[x for x in d["guarantees"] if x!="NO_NETWORK_ACQUISITION"])),"launcher guarantees incomplete"),
      ("fixed_repo_root_reintroduced",lambda r:mutate_text(r,LAUNCHER,lambda s:s.replace('[string]$RepoRoot,','[string]$RepoRoot = "D:\\STALE\\Hydra",')),"launcher must not hard-code a workstation repo root"),
      ("launcher_network_added",lambda r:mutate_text(r,LAUNCHER,lambda s:s+"\nInvoke-WebRequest https://example.com\n"),"launcher unexpectedly performs network acquisition"),
      ("private_capture_exit_removed",lambda r:mutate_text(r,PRIVATE_CAPTURE_LAUNCHER,lambda s:s.replace('Write-Host "ERROR=SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 browser capture is closed."\nexit 1','Write-Host "ERROR=SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 browser capture is closed."',1)),"private capture launcher must exit before creating its private runtime"),
      ("capture_api_quarantine_guard_removed",lambda r:mutate_text(r,CAPTURE_RUNNER,lambda s:s.replace("    reject_quarantined_capture_item(item, capture_locator)\n","",1)),"capture_one quarantine guard missing"),
      ("quarantine_source_version_marker_removed",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('    "source_version_id",\n    "capture_intent_id",','    "capture_intent_id",',1)),"canonical quarantine projection missing stable identity marker: source_version_id"),
      ("micron_provider_domain_removed",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('FORBIDDEN_CAPTURE_PROVIDER_DOMAINS = ("micron.com", "globenewswire.com")','FORBIDDEN_CAPTURE_PROVIDER_DOMAINS = ("globenewswire.com",)',1)),"shared capture guard must pin both forbidden provider domains"),
      ("globenewswire_provider_domain_removed",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('FORBIDDEN_CAPTURE_PROVIDER_DOMAINS = ("micron.com", "globenewswire.com")','FORBIDDEN_CAPTURE_PROVIDER_DOMAINS = ("micron.com",)',1)),"shared capture guard must pin both forbidden provider domains"),
      ("provider_domain_suffix_boundary_weakened",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('normalized_host == domain or normalized_host.endswith("." + domain)','normalized_host.endswith(domain)',1)),"shared capture guard must use suffix-safe provider-domain matching"),
      ("authority_backslash_reopened",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('FORBIDDEN_SPECIAL_SCHEME_AUTHORITY_CHARACTERS = ("\\\\", "%")','FORBIDDEN_SPECIAL_SCHEME_AUTHORITY_CHARACTERS = ("%",)',1)),"shared capture guard must reject browser-ambiguous authority characters"),
      ("authority_percent_encoding_reopened",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('FORBIDDEN_SPECIAL_SCHEME_AUTHORITY_CHARACTERS = ("\\\\", "%")','FORBIDDEN_SPECIAL_SCHEME_AUTHORITY_CHARACTERS = ("\\\\",)',1)),"shared capture guard must reject browser-ambiguous authority characters"),
      ("noncanonical_https_authority_allowed",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('if locator[: len(scheme_prefix)].lower() != scheme_prefix:','if False:',1)),"shared capture guard must require canonical HTTP(S) scheme and authority"),
      ("browser_request_route_guard_removed",lambda r:mutate_text(r,CAPTURE_RUNNER,lambda s:s.replace('        page.route("**/*", guard_provider_request)\n','',1)),"capture_one must install provider request routing before navigation"),
      ("browser_request_callback_policy_removed",lambda r:mutate_text(r,CAPTURE_RUNNER,lambda s:s.replace('            reject_forbidden_capture_request(request_url)\n','',1)),"page route callback must validate each browser request before dispatch"),
      ("pdf_redirect_provider_check_removed",lambda r:mutate_text(r,CAPTURE_RUNNER,lambda s:s.replace('        reject_forbidden_capture_request(next_url)\n','',1)),"PDF redirect destinations must be checked before each request"),
      ("direct_backslash_regression_removed",lambda r:mutate_text(r,"tools/test_constraint_second_slice_batch026_blocked_sources.py",lambda s:s.replace(r'https://micron.com\\@evil.com/source.pdf','')),"direct pre-navigation regression missing URL: https://micron.com\\\\@evil.com/source.pdf"),
      ("direct_percent_encoded_host_regression_removed",lambda r:mutate_text(r,"tools/test_constraint_second_slice_batch026_blocked_sources.py",lambda s:s.replace("https://%6dicron.com/source.pdf",'')),"direct pre-navigation regression missing URL: https://%6dicron.com/source.pdf"),
      ("redirect_request_regression_removed",lambda r:mutate_text(r,"tools/test_constraint_second_slice_batch026_blocked_sources.py",lambda s:s.replace('                redirected = FakeRoute("https://micron.com/redirected.pdf")','                redirected = FakeRoute("https://example.com/redirected.pdf")',1)),"redirect regression must prove blocked provider request is aborted before dispatch"),
      ("pdf_redirect_regression_removed",lambda r:mutate_text(r,"tools/test_constraint_batch026_pdf_raw_response.py",lambda s:s.replace('"Location": "https://%6dicron.com/redirected.pdf"','"Location": "https://example.com/redirected.pdf"',1)),"raw-PDF regression must block a forbidden redirect before its second request"),
      ("effective_capture_locator_check_removed",lambda r:mutate_text(r,"tools/constraint_source_quarantine.py",lambda s:s.replace('for locator_field in ("source_locator", "capture_locator"):','for locator_field in ("source_locator",):',1)),"shared capture guard must inspect source and effective capture locators"),
      ("manual_prep_reopened",lambda r:mutate_text(r,LAUNCHER,lambda s:s.replace('if ($Mode -ne "ContractCheck") {','if ($Mode -eq "NeverContractCheck") {',1)),"launcher token missing: if ($Mode -ne \"ContractCheck\")"),
      ("manual_failure_bypassed",lambda r:mutate_text(r,LAUNCHER,lambda s:s.replace('Fail ("SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 " + $Mode','Write-Host ("SUPERSEDED_BY_BATCH030_QUARANTINE: Batch026 " + $Mode',1)),"Batch026 operational mode gate must fail with the supersession error"),
      ("mtime_inference_added",lambda r:mutate_text(r,LAUNCHER,lambda s:s+"\n# LastWriteTime\n"),"launcher infers capture timestamp from file metadata"),
      ("status_materialized_faked",lambda r:mutate_json(r,STATUS,lambda d:d["results"].__setitem__("RAW_SOURCE_VERSIONS_MATERIALIZED",41)),"Batch027 status metric drifted: RAW_SOURCE_VERSIONS_MATERIALIZED"),
      ("status_release_faked",lambda r:mutate_json(r,STATUS,lambda d:d["results"].__setitem__("T1_RELEASE_MANIFEST_PRESENT","YES")),"Batch027 status metric drifted: T1_RELEASE_MANIFEST_PRESENT"),
      ("master_replay_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["SECOND_SLICE_REPLAY_READY"].__setitem__("status","YES")),"master falsely claims replay ready"),
      ("master_full_ready",lambda r:mutate_json(r,MASTER,lambda d:d["readiness"]["FULL_CONSTRAINT_RUN_READY"].__setitem__("status","YES")),"master falsely full-run ready"),
    ];
    for x in cases: expect(*x)
    print("CONSTRAINT_SECOND_SLICE_BATCH027_HOSTILE_MATRIX=PASS")
    print(f"HOSTILE_CASES={len(cases)}")
    return 0

if __name__=="__main__": raise SystemExit(main())
