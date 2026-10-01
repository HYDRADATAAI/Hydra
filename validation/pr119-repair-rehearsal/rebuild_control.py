"""Localize the preserved byte failure; no normalization is accepted as a PASS."""
import hashlib,json,os,platform,subprocess,sys
from pathlib import Path
MAIN='fa94ab3e2fdd4776d84d110f4233ba84409eb947'
REHEARSAL='c7f63bc836bfb1bf1e6e1ee9445ffd4d8f6c6227'
BUILDER='tools/build_constraint_second_slice_batch034_t2_evidence_lineage.py'
BINDING='docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_SEMICONDUCTOR_ORDINARY_T2_EVIDENCE_LINEAGE_BINDING_V001_20260928.json'
if os.name!='nt':raise SystemExit('Windows required')
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
commands=[];results=[]
def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
def run(args,cwd):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True)
    commands.append({'argv':list(map(str,args)),'cwd':str(cwd),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
    save('control_commands.json',commands)
    return p
def git(cwd,*args):
    p=run(['git',*args],cwd)
    if p.returncode:raise RuntimeError(p.stderr)
    return p.stdout.strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(cwd):return {p:digest(cwd/p) for p in git(cwd,'ls-files').splitlines()}
if git(root,'rev-parse','HEAD')!=REHEARSAL:raise SystemExit('Wrong source')
main=root.parent/'main_control'
git(root,'-c','core.autocrlf=false','worktree','add','--detach',str(main),MAIN)
for name,path in [('rehearsal',root),('main',main)]:
    before=snapshot(path);save(name+'_before.json',before)
    rebuilt=out/(name+'_binding.json')
    p=run([sys.executable,'-B',str(path/BUILDER),'--output',str(rebuilt)],path)
    a=(path/BINDING).read_bytes();b=rebuilt.read_bytes()
    after=snapshot(path);save(name+'_after.json',after)
    result={'source':name,'head':git(path,'rev-parse','HEAD'),'tree':git(path,'rev-parse','HEAD^{tree}'),'builder_exit':p.returncode,
       'builder_sha256':digest(path/BUILDER),'original_sha256':digest(path/BINDING),'rebuilt_sha256':digest(rebuilt),
       'original_bytes':len(a),'rebuilt_bytes':len(b),'original_CRLF_count':a.count(b'\r\n'),'rebuilt_CRLF_count':b.count(b'\r\n'),
       'raw_byte_equality':a==b,'JSON_equal':json.loads(a)==json.loads(b),
       'CRLF_to_LF_equal_diagnostic_only':a==b.replace(b'\r\n',b'\n'),
       'source_hashes_stable':before==after,'status':git(path,'status','--porcelain=v1')}
    results.append(result);save('control_results.json',results)
    print(json.dumps(result),flush=True)
proof=all(r['builder_exit']==0 and not r['raw_byte_equality'] and r['JSON_equal'] and r['CRLF_to_LF_equal_diagnostic_only'] and r['source_hashes_stable'] and not r['status'] for r in results)
proof=proof and results[0]['builder_sha256']==results[1]['builder_sha256'] and results[0]['original_sha256']==results[1]['original_sha256'] and results[0]['rebuilt_sha256']==results[1]['rebuilt_sha256']
save('control_summary.json',{'diagnostic_reproduction':'PASS' if proof else 'FAIL','rehearsal_byte_check':'FAIL_RETAINED','main_byte_check':'FAIL_RETAINED','classification':'POST_V005_MAIN_DRIFT' if proof else 'UNKNOWN','normalization_accepted_as_pass':False,'python':sys.version,'platform':platform.platform(),'scope':'DIAGNOSTIC_ONLY_NOT_CANDIDATE_ACCEPTANCE'})
save('control_hashes.json',{p.name:digest(p) for p in out.iterdir() if p.is_file() and p.name!='control_hashes.json'})
raise SystemExit(0 if proof else 1)
