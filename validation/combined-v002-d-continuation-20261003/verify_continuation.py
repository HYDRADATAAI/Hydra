"""Windows exact-C dependency and separate live-ref/equivalence checks."""
import hashlib,json,os,subprocess,sys
from pathlib import Path

def main():
    root=Path(sys.argv[1]).resolve();matrix=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve()
    if os.name!='nt' or any(p.drive.upper()!='D:' for p in [root,matrix,out]):raise SystemExit('Windows D: required')
    here=Path(__file__).resolve().parent;pins=json.loads((here/'freshness_inputs.json').read_text());proof=json.loads((here/'equivalence_inputs.json').read_text())
    checks=[];commands=[]
    def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
    def check(name,ok,detail=None):
        checks.append({'name':name,'passed':bool(ok),'detail':detail})
        if not ok:raise RuntimeError(name)
    def git(*args):
        r=subprocess.run(['git',*args],cwd=root,capture_output=True,text=True)
        commands.append({'argv':['git',*args],'cwd':str(root),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if r.returncode:raise RuntimeError('git '+str(args)+': '+r.stderr)
        return r.stdout.strip()
    def tree(ref):return {line.split('\t',1)[1]:line.split('\t',1)[0] for line in git('ls-tree','-r',ref).splitlines()}
    def delta(before,after):return sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p))
    result={'result':'FAIL','tested_source':pins['tested_source'],'tested_tree':pins['tested_tree'],'C_original_run':pins['C_run_id'],'C_archive_sha256':pins['C_archive_sha256'],'C_manifest_sha256':pins['C_manifest_sha256'],'live_main':pins['live_main'],'current_PR146':pins['current_PR146'],'C_execution_claim_for_current_PR146':False}
    try:
        check('C_manifest_exact_bytes',hashlib.sha256((matrix/'report_hashes.json').read_bytes()).hexdigest()==pins['C_manifest_sha256'])
        manifest=read(matrix/'report_hashes.json');bad=[p for p,h in manifest.items() if hashlib.sha256((matrix/p).read_bytes()).hexdigest()!=h]
        check('all_C_manifest_members',not bad,{'count':len(manifest),'bad':bad})
        c=read(matrix/'summary.json')
        check('C_exact_historical_binding',c['candidate_commit']==pins['tested_source'] and c['candidate_tree']==pins['tested_tree'] and c['current_main']==pins['C_original_main'] and c['pr143_head']==pins['merged_pr143'],c)
        check('C_full_result',c['result']=='PASS' and c['test_reports']=={'passed':535,'failed':0,'skipped':0} and c['subtest_reports']=={'passed':797,'failed':0,'skipped':0} and c['command_totals']=={'pass':40,'fail':0} and not c['checks_failed'],c)
        groups=read(matrix/'matrix.json');check('C_all_fifteen_groups',len(groups)==15 and all(v['status']=='PASS' for v in groups.values()))
        frozen_harness=here.parent/'combined-v002-20261003'
        sys.path.insert(0,str(frozen_harness))
        from report_gate import validate_execution_reports
        reports=read(matrix/'pytest_results.json')
        errors=validate_execution_reports(reports,expected_count=535,permitted_skip_methods=set())
        check('C_terminal_accounting',not errors,errors)
        check('immutable_source_identity',git('rev-parse','HEAD')==pins['tested_source'] and git('rev-parse','HEAD^{tree}')==pins['tested_tree'])
        check('immutable_source_clean',not git('status','--porcelain=v1','--untracked-files=all'))
        maps={name:tree(ref) for name,ref in [('tested',pins['tested_source']),('main',pins['live_main']),('PR143',pins['merged_pr143']),('PR146',pins['current_PR146'])]}
        check('all_four_file_counts',all(len(m)==741 for m in maps.values()),{k:len(v) for k,v in maps.items()})
        check('main_tree_exact_merged_PR143',maps['main']==maps['PR143'] and git('rev-parse',pins['live_main']+'^{tree}')==pins['live_main_tree'])
        check('main_exact_parents',git('show','-s','--format=%P',pins['live_main']).split()==[pins['C_original_main'],pins['merged_pr143']])
        check('PR146_exact_parent_tree',git('show','-s','--format=%P',pins['current_PR146']).split()==[pins['tested_source']] and git('rev-parse',pins['current_PR146']+'^{tree}')==pins['current_PR146_tree'])
        for label,before,after,rows,count in [('main_to_tested','main','tested',proof['main_to_tested_source'],3),('tested_to_PR146','tested','PR146',proof['tested_source_to_live_pr146'],2)]:
            wanted=sorted(row['path'] for row in rows)
            check(label+'_scope',len(rows)==count and delta(maps[before],maps[after])==wanted,wanted)
            for row in rows:
                check(label+'_exact_blob_'+row['path'],all(maps[which][row['path']]==row[key]['mode']+' '+row[key]['type']+' '+row[key]['sha'] for which,key in [(before,'before'),(after,'after')]),row)
        check('PR146_all_other739_paths_exact',len([p for p in maps['tested'] if maps['tested'][p]==maps['PR146'].get(p)])==739)
        before=read(matrix/'source_hashes_before.json');after=read(matrix/'source_hashes_after.json')
        observed={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in maps['tested']}
        check('source_all741_hashes_equal_C',len(observed)==741 and observed==before==after)
        for ref,expected in [('refs/heads/main',pins['live_main']),('refs/heads/nyx/thread-h-temporal-consistency-20261003',pins['merged_pr143']),(pins['current_PR146_ref'],pins['current_PR146'])]:
            lines=git('ls-remote','origin',ref).splitlines()
            check('strict_live_ref_'+ref,len(lines)==1 and lines[0].split()==[expected,ref],lines)
        result['result']='PASS'
    except Exception as exc:result['error']=repr(exc)
    result.update(checks=checks,commands=commands,checks_failed=[c['name'] for c in checks if not c['passed']])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'commands','checks'}},indent=2))
    return 0 if result['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
