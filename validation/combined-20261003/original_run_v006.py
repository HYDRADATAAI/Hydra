"""Windows V006, gated on the exact repaired candidate's full matrix."""
import hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

def main():
    if os.name!='nt':raise SystemExit('Windows required')
    root=Path(sys.argv[1]).resolve(); matrix=Path(sys.argv[2]).resolve(); out=Path(sys.argv[3]).resolve()
    if any(p.drive.upper()!='D:' for p in [root,matrix,out]):raise SystemExit('D: required')
    out.mkdir(parents=True,exist_ok=True)
    pins=json.loads((Path(__file__).parent/'candidate_inputs.json').read_text())
    commands=[]; checks=[]; skips=[]
    def save(name,data):(out/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    def run(label,args,cwd=root,env=None,allowed_failure=False):
        started=time.time();p=subprocess.run(list(map(str,args)),cwd=cwd,env=env,text=True,capture_output=True,timeout=180)
        log=out/(label+'.log');log.write_text(p.stdout+p.stderr,encoding='utf-8')
        commands.append({'label':label,'argv':list(map(str,args)),'cwd':str(cwd),'exit_code':p.returncode,'duration_seconds':round(time.time()-started,3),'log':log.name,'PYTHONPATH':(env or os.environ).get('PYTHONPATH')})
        save('commands.json',commands)
        if p.returncode and not allowed_failure:raise RuntimeError(label+': '+p.stdout+p.stderr)
        return p
    def git(label,repo,*args,cwd=None):return run(label,['git','-C',str(repo),*args],cwd=cwd or repo).stdout.strip()
    def check(name,passed,detail):
        checks.append({'name':name,'passed':bool(passed),'detail':detail});save('checks.json',checks)
        if not passed:raise RuntimeError(name)
    def snapshot(repo,label):
        files=git(label+'_files',repo,'ls-files','-z').split('\0')
        return {p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in files if p}
    def status(repo,label):
        return {'head':git(label+'_head',repo,'rev-parse','HEAD'),'tree':git(label+'_tree',repo,'rev-parse','HEAD^{tree}'),'status':git(label+'_status',repo,'status','--porcelain=v1','--untracked-files=all')}
    summary={'result':'FAIL','candidate_commit':pins['candidate_commit'],'candidate_tree':pins['candidate_tree'],'current_main':pins['main'],'pr119_head':pins['pr119_head'],'scope':'HOSTED_WINDOWS_PUBLIC_REPOSITORY_FIXTURES','user_workstation_tested':False,'admission_claimed':False,'readiness_claimed':False,'production_approval_claimed':False}
    before=None; worktree=None
    try:
        dependency=json.loads((matrix/'summary.json').read_text())
        check('changed_from_V005',pins['candidate_tree']!=pins['v005_tree'],{'current_tree':pins['candidate_tree'],'V005_tree':pins['v005_tree']})
        check('C_result',dependency['result'] in ['PASS','PASS_WITH_ALLOWED_SKIPS'],dependency['result'])
        check('C_exact_binding',dependency['candidate_commit']==pins['candidate_commit'] and dependency['candidate_tree']==pins['candidate_tree'] and dependency['current_main']==pins['main'] and dependency['pr119_head']==pins['pr119_head'],dependency)
        manifest=json.loads((matrix/'report_hashes.json').read_text())
        bad=[p for p,h in manifest.items() if hashlib.sha256((matrix/p).read_bytes()).hexdigest()!=h]
        check('C_member_hashes',not bad,{'members':len(manifest),'mismatches':bad})
        groups=json.loads((matrix/'matrix.json').read_text())
        check('C_fifteen_groups',len(groups)==15 and all(g['status'] in ['PASS','PASS_WITH_ALLOWED_SKIPS'] for g in groups.values()),{k:g['status'] for k,g in groups.items()})
        save('dependency_binding.json',{'summary':dependency,'matrix_manifest_sha256':hashlib.sha256((matrix/'report_hashes.json').read_bytes()).hexdigest(),'matrix_member_hashes':manifest})
        initial=status(root,'source_initial')
        check('source_initial_identity',initial=={'head':pins['candidate_commit'],'tree':pins['candidate_tree'],'status':''},initial)
        before=snapshot(root,'source_before');save('source_hashes_before.json',before)
        check('source_matches_C_end',before==json.loads((matrix/'source_hashes_after.json').read_text()),{'count':len(before)})
        git_entries=git('source_tree_entries',root,'ls-tree','-r','HEAD').splitlines()
        differences=[]
        for row in git_entries:
            info,path=row.split('\t',1);mode,kind,digest=info.split();data=(root/path).read_bytes()
            observed=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if kind!='blob' or mode=='120000' or observed!=digest:differences.append(path)
        check('source_exact_Git_bytes',not differences,{'files':len(before),'mismatches':differences})
        check('source_count',len(before)==pins['file_count'],len(before))
        for ref,expected in [('refs/heads/main',pins['main']),('refs/heads/nyx/timestamp-hash-attestation-integration-20260928',pins['pr119_head'])]:
            observed=git('remote_'+('main' if ref.endswith('/main') else 'pr119'),root,'ls-remote','origin',ref).split()[0]
            check('remote_pin_'+ref,observed==expected,observed)
        skips=json.loads((matrix/'skip_inventory.json').read_text())
        check('C_skip_adjudication',all(x.get('allowed') is True for x in skips),skips)
        tests=json.loads((matrix/'pytest_results.json').read_text())
        names=['test_symlinked_object_tree_into_public_repo_is_rejected','test_symlinked_receipt_tree_into_public_repo_is_rejected','test_symlinked_release_tree_into_public_repo_is_rejected','test_symlinked_object_tree_outside_private_root_is_rejected']
        symlink_rows=[]
        for name in names:
            rows=[r for r in tests['reports'] if r['nodeid'].endswith('::'+name) and (r['phase']=='call' or r['outcome']=='skipped')]
            check('symlink_case_'+name,bool(rows) and all(r['outcome'] in ['passed','skipped'] for r in rows),rows)
            symlink_rows.extend(rows)
        save('symlink_test_inventory.json',symlink_rows)
        outside=out.parent/'outside context'/('nested_'+('a'*50))/('nested_'+('b'*50))
        outside.mkdir(parents=True,exist_ok=True)
        worktree=out.parent/'deep worktree with spaces'/('nested_'+('c'*50))/'candidate'
        worktree.parent.mkdir(parents=True,exist_ok=True)
        git('worktree_add',root,'-c','core.autocrlf=false','worktree','add','--detach',str(worktree),pins['candidate_commit'])
        git('worktree_autocrlf',worktree,'config','core.autocrlf','false')
        check('linked_worktree_git_file',(worktree/'.git').is_file(),str(worktree/'.git'))
        worktree_before=snapshot(worktree,'worktree_before');save('worktree_hashes_before.json',worktree_before)
        check('linked_worktree_exact_bytes',worktree_before==before,{'count':len(worktree_before)})
        script_names=['validate_constraint_first_slice_successor.py','validate_constraint_first_slice_custody.py','validate_constraint_second_slice_batch034_t2_evidence_lineage.py']
        for context,repo,cwd in [('ordinary',root,root),('outside_deep_cwd',root,outside),('linked_worktree_outside_cwd',worktree,outside)]:
            top=git(context+'_toplevel',repo,'rev-parse','--show-toplevel',cwd=cwd)
            check(context+'_toplevel',Path(top).resolve()==repo.resolve(),top)
            git(context+'_object_path',repo,'rev-parse','--git-path','objects',cwd=cwd)
            env=os.environ.copy();env['PYTHONPATH']=str(repo/'constraint-t1-raw-artifact-store/src')+os.pathsep+env.get('PYTHONPATH','')
            for script in script_names:
                run(context+'_'+script.removesuffix('.py'),[sys.executable,'-B',str(repo/'tools'/script)],cwd=cwd,env=env)
            sample='tools/validate_constraint_first_slice_successor.py'
            observed=git(context+'_hash_object',repo,'hash-object',str(repo/sample),cwd=cwd)
            expected=git(context+'_expected_blob',repo,'rev-parse','HEAD:'+sample,cwd=cwd)
            check(context+'_Git_path_hash',observed==expected,{'observed':observed,'expected':expected})
        target=out.parent/'symlink probe target';target.mkdir(exist_ok=True)
        link=out.parent/'symlink probe link'
        try:
            link.symlink_to(target,target_is_directory=True)
            check('directory_symlink_resolves',link.is_symlink() and link.resolve()==target.resolve(),{'link':str(link),'target':str(target)})
            link.unlink()
        except OSError as exc:
            if getattr(exc,'winerror',None)!=1314:raise
            skips.append({'nodeid':'V006::directory_symlink_permission_probe','outcome':'skipped','allowed':True,'winerror':1314,'category':'KNOWN_DIRECTORY_SYMLINK_PERMISSION','detail':str(exc)})
        worktree_after=snapshot(worktree,'worktree_after');save('worktree_hashes_after.json',worktree_after)
        worktree_status=status(worktree,'worktree_final');save('worktree_final_status.json',worktree_status)
        check('worktree_hashes_stable',worktree_before==worktree_after,{'count':len(worktree_after)})
        check('worktree_clean',worktree_status=={'head':pins['candidate_commit'],'tree':pins['candidate_tree'],'status':''},worktree_status)
        git('worktree_remove',root,'worktree','remove',str(worktree))
        summary['matrix_test_methods']=dependency['test_reports'];summary['matrix_subtests']=dependency['subtest_reports']
        summary['matrix_command_totals']=dependency['command_totals'];summary['source_file_count']=len(before)
        summary['result']='PASS_WITH_ALLOWED_SKIPS' if skips else 'PASS'
    except Exception as exc:
        summary['error']=repr(exc)
    finally:
        try:
            after=snapshot(root,'source_after');save('source_hashes_after.json',after)
            final=status(root,'source_final');save('final_repository_status.json',final)
            stable=before is not None and before==after
            checks.append({'name':'source_hashes_stable','passed':stable,'detail':{'count':len(after)}})
            if not stable or final!={'head':pins['candidate_commit'],'tree':pins['candidate_tree'],'status':''}:summary['result']='FAIL'
        except Exception as exc:summary.update(result='FAIL',final_verification_error=repr(exc))
        save('environment.json',{'python':sys.version,'platform':platform.platform(),'executable':sys.executable,'run_id':os.environ.get('GITHUB_RUN_ID'),'source':str(root),'matrix':str(matrix),'out':str(out)})
        save('skip_inventory.json',skips);save('checks.json',checks)
        summary['command_count']=len(commands);summary['skip_count']=len(skips)
        summary['checks_failed']=[x['name'] for x in checks if not x['passed']]
        save('summary.json',summary)
        save('report_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='report_hashes.json'})
        print(json.dumps(summary,indent=2),flush=True)
    return 0 if summary['result'] in ['PASS','PASS_WITH_ALLOWED_SKIPS'] else 1

if __name__=='__main__':raise SystemExit(main())
