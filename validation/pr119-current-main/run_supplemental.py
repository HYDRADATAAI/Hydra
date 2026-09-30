"""Differential rejection tests on exact candidate and unchanged current main."""
import ast, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

MAIN='fa94ab3e2fdd4776d84d110f4233ba84409eb947'
PREVIEW='c0fc3ece522c9a4441d15e20501b6d1519443450'
TREE='73f8d2a8903da6be8397124e8baa4d292dffdbac'
BASE='bf74ad8352cc8681b374e185772085212619f00f'

def main():
    if os.name!='nt':raise SystemExit('Windows required')
    source=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve(); out.mkdir(parents=True,exist_ok=True)
    harness=Path(__file__).resolve().parent; records=[]
    def save(name,data): (out/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
    def hashes(root):return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git(root,'ls-files').splitlines()}
    if git(source,'rev-parse','HEAD')!=PREVIEW or git(source,'rev-parse','HEAD^{tree}')!=TREE:raise SystemExit('Candidate identity mismatch')
    mainroot=source.parent/'main'
    subprocess.run(['git','-C',str(source),'worktree','add','--detach',str(mainroot),MAIN],check=True)
    save('environment.json',{'python':sys.version,'platform':platform.platform(),'candidate':PREVIEW,'tree':TREE,'current_main':MAIN,'historical_base':BASE})
    save('provenance.json',{'thread_e_test_sha256':hashlib.sha256((harness/'test_unresolved_gates.py').read_bytes()).hexdigest(),
        'thread_e_test_commit':'83ada07d886ce52b926120543ebd2f0cdf249313',
        'thread_f_original_sha256':hashlib.sha256((harness/'thread_f_original.py').read_bytes()).hexdigest(),
        'thread_f_adaptation':'Only PIN changes from current main to exact preview for candidate invocation. Test method ASTs must match.'})
    def run(label,args,root,env):
        start=time.time(); log=out/(label+'.log')
        with log.open('w',encoding='utf-8') as f:
            p=subprocess.run(args,cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT,text=True,timeout=600)
        records.append({'label':label,'argv':list(map(str,args)),'cwd':str(root),'exit_code':p.returncode,'duration_seconds':time.time()-start,'PYTHONPATH':env['PYTHONPATH'],'log':log.name})
        save('commands.json',records);print(label+' exit='+str(p.returncode),flush=True)
    for name,root,pin in [('candidate',source,PREVIEW),('main',mainroot,MAIN)]:
        before=hashes(root);save(name+'_source_before.json',before)
        env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(root/'constraint-runtime/src'),str(root/'constraint-runtime/tests'),str(harness),env.get('PYTHONPATH','')])
        env['PYTHONDONTWRITEBYTECODE']='1';env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
        env['MATRIX_INVENTORY']=str(out/(name+'_E_inventory.json'));env['MATRIX_RESULTS']=str(out/(name+'_E_results.json'))
        run(name+'_E_unresolved_gates',[sys.executable,'-m','pytest','--import-mode=importlib','-p','pytest_subtests.plugin','-p','matrix_reporter','-p','no:cacheprovider',str(harness/'test_unresolved_gates.py'),'-vv','--tb=long','--junitxml='+str(out/(name+'_E.xml'))],root,env)
        original=(harness/'thread_f_original.py').read_text(encoding='utf-8')
        adapted=original.replace("PIN='"+MAIN+"'","PIN='"+pin+"'")
        a=[ast.dump(n) for n in ast.walk(ast.parse(original)) if isinstance(n,ast.FunctionDef)]
        b=[ast.dump(n) for n in ast.walk(ast.parse(adapted)) if isinstance(n,ast.FunctionDef)]
        if a!=b:raise RuntimeError('Test method adaptation drift')
        copy=out/(name+'_thread_f_bound.py');copy.write_text(adapted,encoding='utf-8')
        run(name+'_F_non_escalation',[sys.executable,'-B',str(copy),'--repo',str(root),'--json-output',str(out/(name+'_F_results.json'))],root,env)
        after=hashes(root);save(name+'_source_after.json',after)
        save(name+'_source_status.json',{'head':git(root,'rev-parse','HEAD'),'tree':git(root,'rev-parse','HEAD^{tree}'),'status':git(root,'status','--porcelain=v1'),'hashes_unchanged':before==after})
    # File identity plus identical rejection results localizes post-V005 main additions.
    c=hashes(source);m=hashes(mainroot)
    focus=[p for p in c if p.startswith('constraint-runtime/') or 'batch034' in p.lower() or 'ordinary_t2_evidence_lineage' in p.lower()]
    historical=set(git(source,'ls-tree','-r','--name-only',BASE).splitlines())
    save('localization_inputs.json',{'candidate_vs_main_equal':{p:c[p]==m.get(p) for p in focus},'absent_in_historical_base':[p for p in focus if p not in historical],
         'classification':'POST_V005_MAIN_DRIFT when identical main/candidate failures reproduce; this harness does not repair candidate source.'})
    save('report_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='report_hashes.json'})
    return 1 if any(r['exit_code'] for r in records) else 0

if __name__=='__main__':raise SystemExit(main())
