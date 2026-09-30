"""Correct only the missing required CLI argument; preserve previous run evidence."""
import hashlib,json,os,platform,subprocess,sys
from pathlib import Path

PIN='c0fc3ece522c9a4441d15e20501b6d1519443450'
TREE='73f8d2a8903da6be8397124e8baa4d292dffdbac'
if os.name!='nt':raise SystemExit('Windows required')
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
if git('rev-parse','HEAD')!=PIN or git('rev-parse','HEAD^{tree}')!=TREE:raise SystemExit('Exact identity mismatch')
def hashes():return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git('ls-files').splitlines()}
before=hashes()
args=[sys.executable,'tools/validate_constraint_t1_first_slice_attestation.py','--attestation','docs/constraint/validation/HYDRA_CONSTRAINT_BATCH018_T1_NINE_SOURCE_MATERIALIZATION_ATTESTATION_V001_20260926.json']
r=subprocess.run(args,cwd=root,text=True,capture_output=True)
(out/'attestation_corrected.stdout').write_text(r.stdout,encoding='utf-8')
(out/'attestation_corrected.stderr').write_text(r.stderr,encoding='utf-8')
after=hashes();status=git('status','--porcelain=v1')
report={'candidate':PIN,'tree':TREE,'python':sys.version,'platform':platform.platform(),'argv':args,'cwd':str(root),'exit_code':r.returncode,'source_hashes_stable':before==after,'status':status,'reason':'Original harness invocation omitted mandatory --attestation and exited 2 before validation. This run supplies the exact committed Batch018 public attestation. No tests or source bytes are changed.','previous_run_id':36791134767,'github_run_id':os.environ.get('GITHUB_RUN_ID')}
for name,data in [('correction.json',report),('source_before.json',before),('source_after.json',after)]:
 (out/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(r.stdout);print(json.dumps(report,indent=2))
raise SystemExit(0 if r.returncode==0 and before==after and not status else 1)
