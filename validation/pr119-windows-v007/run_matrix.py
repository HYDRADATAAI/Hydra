"""Read-only exact-candidate validation. Execute HYDRA tests only on Windows."""
from __future__ import annotations
import ast
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

MAIN = '8b459719619be497408bdf970b8d1e8830ce93b3'
HEAD = '417174daa31761ad9eaeba56ca6306b3050ada7a'
BASE = 'bf74ad8352cc8681b374e185772085212619f00f'
ORIGINAL = 'c0fc3ece522c9a4441d15e20501b6d1519443450'
PREVIEW = 'eb46eff603299414f427161fd07ae9a074f4ffd6'
REPAIRS = ['53ac6e28cb3088bdaf5d7c2702f44f362998892f','eaa256a809075361e463ba0dd3dc299dcbf1b5dc']
TREE = '23837f20645666b910a80cb53b5c4f4eb243c85b'
PACKAGES = ['constraint-physical-dependency','constraint-geopolitical-policy',
            'constraint-replay','constraint-t1-raw-artifact-store',
            't6-fail-closed-validator','constraint-runtime']
SCRIPTS = [
 'validate_constraint_first_slice_successor.py',
 'test_constraint_first_slice_adversarial.py',
 'validate_constraint_first_slice_acceptance_gate.py',
 'test_constraint_first_slice_acceptance_gate_adversarial.py',
 'validate_constraint_first_slice_confidence_evaluation.py',
 'test_constraint_first_slice_confidence_evaluation_adversarial.py',
 'validate_constraint_first_slice_outcome_coverage.py',
 'test_constraint_first_slice_outcome_coverage_adversarial.py',
 'validate_constraint_first_slice_custody.py',
 'test_constraint_first_slice_custody_adversarial.py',
 'validate_constraint_lily_owner_seams.py',
 'nyx_validate_constraint_successor_chain.py',
 'nyx_test_constraint_successor_chain_adversarial.py',
 'validate_constraint_t1_first_slice_attestation.py',
 'validate_constraint_second_slice_batch033_ordinary_t2_normalization.py',
 'test_constraint_second_slice_batch033_ordinary_t2_normalization_adversarial.py',
 'validate_constraint_second_slice_batch034_t2_evidence_lineage.py',
 'test_constraint_second_slice_batch034_t2_evidence_lineage_adversarial.py',
 'validate_public_repository.py',
 'test_constraint_second_slice_batch034_builder_bytes.py',
]
GROUPS = {
 '01_T1_raw_artifact_store':['constraint-t1-raw-artifact-store/tests/'],
 '02_first_slice_integration':['first_slice','integrated_owners'],
 '03_owner_seam_conformance':['test_lily_owner_seam','validate_constraint_lily_owner_seams'],
 '04_successor_chain_hostile':['nyx_test_constraint_successor_chain_adversarial'],
 '05_Batch018_evidence_alignment':['test_batch018_nine_source_capture_evidence_alignment'],
 '06_Batch033_custody_continuation':['test_batch033_custody_continuation'],
 '07_timestamp_gate_successor':['test_timestamp_gate','test_timestamp_successor_binding','test_restack_successor_binding'],
 '08_Batch034_evidence_lineage':['test_ordinary_t2_evidence_lineage','batch034_t2_evidence_lineage','test_constraint_second_slice_batch034_builder_bytes'],
 '09_Constraint_V018_runtime':['constraint-runtime/tests/'],
 '10_public_repository_hygiene':['validate_public_repository','public_root_hygiene'],
 '11_governed_compile_AST':['compile_runtime','governed_ast'],
 '12_manifest_hash_validators':['nyx_validate_constraint_successor_chain','validate_constraint_t1_first_slice_attestation','validate_constraint_second_slice_batch033','validate_constraint_second_slice_batch034','validate_constraint_first_slice_custody'],
 '13_exact_predecessor_recovery':['test_batch033_custody_continuation','test_restack_successor_binding','test_timestamp_successor_binding'],
 '14_unresolved_timestamps':['test_timestamp_gate','test_unverified_metadata_boundary','test_pit_conservative_availability','test_constraint_first_slice_outcome_coverage_adversarial'],
 '15_authority_admission_non_elevation':['test_unresolved_gates','original_F_regressions','test_authority','test_native_binding_admission','test_native_admission_input_types','test_native_t5_t6_bridge','test_constraint_first_slice_acceptance_gate_adversarial','boundary_state'],
}

def main():
    if os.name != 'nt':
        raise SystemExit('Windows required; no HYDRA runtime tests executed.')
    root = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
    harness = Path(__file__).resolve().parent
    if root.drive.upper()!='D:' or out.drive.upper()!='D:': raise SystemExit('D: source and output required')
    inputs=json.loads((harness/'candidate_inputs.json').read_text())
    if inputs['candidate_commit']!=PREVIEW or inputs['candidate_tree']!=TREE: raise SystemExit('Harness input binding mismatch')
    commands=[]; checks=[]
    def save(name, data):
        (out/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    def run(label, args, cwd=root, env=None, timeout=1200):
        start=time.time(); dest=out/(label+'.log')
        command={'label':label,'argv':list(map(str,args)),'cwd':str(cwd),
                 'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                 'environment':{k:(env or os.environ).get(k) for k in ['PYTHONPATH','TEMP','TMP','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONDONTWRITEBYTECODE']}}
        print('START '+label,flush=True)
        with dest.open('w',encoding='utf-8') as f:
            process=subprocess.Popen(args,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,text=True)
            deadline=start+timeout; last=start
            while process.poll() is None:
                time.sleep(1)
                if time.time()-last>=20:
                    print('RUNNING '+label+' '+str(round(time.time()-start))+'s',flush=True); last=time.time()
                if time.time()>deadline:
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                    process.wait(); command['timeout']=True; break
        command.update(exit_code=process.returncode,duration_seconds=round(time.time()-start,3),log=dest.name)
        text=dest.read_text(encoding='utf-8',errors='replace')
        command['custom_pass_lines']=len(re.findall(r'^PASS\s*(?:::|:)',text,re.M))
        command['unittest_totals']=re.findall(r'Ran (\d+) tests? in ([0-9.]+)s',text)
        commands.append(command); save('commands.json',commands)
        print('END '+label+' exit='+str(process.returncode),flush=True)
        return process.returncode,text
    def git(*args):
        r=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True)
        if r.returncode: raise RuntimeError(r.stderr)
        return r.stdout.strip()
    def check(name,condition,detail):
        checks.append({'name':name,'passed':bool(condition),'detail':detail})
    def snapshot():
        return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git('ls-files').splitlines()}
    save('environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),
         'git':git('--version'),'runner_os':os.environ.get('RUNNER_OS'),'github_run_id':os.environ.get('GITHUB_RUN_ID'),
         'candidate_commit':PREVIEW,'candidate_tree':TREE,'current_main':MAIN,'pr119_head':HEAD,
         'historical_base':BASE,'repair_commits':REPAIRS,'original_two_input_candidate':ORIGINAL,'runtime_execution':'HOSTED_WINDOWS_NOT_USER_WORKSTATION'})
    check('candidate_identity',git('rev-parse','HEAD')==PREVIEW and git('rev-parse','HEAD^{tree}')==TREE,git('show','-s','--format=%H %T %P','HEAD'))
    check('parents',git('show','-s','--format=%P','HEAD').split()==[MAIN,HEAD],git('show','-s','--format=%P','HEAD'))
    check('initial_clean_status',not git('status','--porcelain=v1'),git('status','--porcelain=v1'))
    initial=snapshot(); save('source_hashes_before.json',initial)
    if not all(c['passed'] for c in checks):
        save('checks.json',checks); raise SystemExit('Safety precondition failed')
    # Reconstruct current main plus PR119; verify E/F repairs already in main.
    for n in [1,2]:
        code,text=run('reproduce_tree_'+str(n),[sys.executable,str(harness/'reconstruct.py'),str(root),str(out),str(n)])
        check('reproduced_tree_'+str(n),code==0 and text.strip()==TREE,text)
    construction=json.loads((out/'reconstruction_1.json').read_text())
    check('exact_owned_and_main_bytes',construction['passed'],construction)
    save('construction_check.json',checks)
    if not all(c['passed'] for c in checks): raise SystemExit('Construction safety check failed')
    inventory=[]; parsed=[]; ast_errors=[]
    selected=[p for p in initial if p.endswith('.py') and (any(p.startswith(x+'/') for x in PACKAGES) or p in ['tools/'+x for x in SCRIPTS] or p=='tools/build_constraint_second_slice_batch034_t2_evidence_lineage.py')]
    for p in selected:
        try:
            tree=ast.parse((root/p).read_text(encoding='utf-8-sig'),filename=p); parsed.append(p)
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_'):
                    inventory.append({'path':p,'method':node.name,'line':node.lineno})
        except Exception as exc: ast_errors.append({'path':p,'error':repr(exc)})
    save('static_test_inventory.json',inventory)
    save('governed_ast.json',{'parsed':parsed,'errors':ast_errors})
    check('governed_ast',not ast_errors,{'files':len(parsed),'errors':ast_errors})
    bad=[p for p in initial if '/' not in p and (p.endswith(('.zip','.zip.sha256')) or (p.startswith('EXTRACT_') and p.endswith('.ps1')) or re.search(r' \([0-9]+\)\.[^/]+$',p))]
    check('public_root_hygiene',not bad,bad)
    for p in ['state','raw_archive','golden']:
        check('runtime_forbidden_'+p,not (root/'constraint-runtime'/p).exists(),p)
    env=os.environ.copy()
    env['PYTHONPATH']=os.pathsep.join([str(root/p/'src') for p in PACKAGES]+[str(root/'constraint-runtime/tests'),str(harness),env.get('PYTHONPATH','')])
    env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
    env['MATRIX_INVENTORY']=str(out/'collected_tests.json'); env['MATRIX_RESULTS']=str(out/'pytest_results.json')
    testdirs=[p+'/tests' for p in PACKAGES]
    pytest=[sys.executable,'-m','pytest','--rootdir='+str(root),'--import-mode=importlib','-p','pytest_subtests.plugin','-p','matrix_reporter','-p','no:cacheprovider']
    run('collect_all_owners',pytest+testdirs+['--collect-only','-q'],env=env)
    if (out/'collected_tests.json').exists(): (out/'pre_execution_collection.json').write_bytes((out/'collected_tests.json').read_bytes())
    run('integrated_owners',pytest+testdirs+['-vv','--tb=long','--junitxml='+str(out/'tests.xml')],env=env)
    run('compile_runtime',[sys.executable,'-m','compileall','-q','constraint-runtime/src'],env=env)
    for script in SCRIPTS:
        args=[sys.executable,'tools/'+script]
        if script=='validate_constraint_t1_first_slice_attestation.py':
            args+=['--attestation','docs/constraint/validation/HYDRA_CONSTRAINT_BATCH018_T1_NINE_SOURCE_MATERIALIZATION_ATTESTATION_V001_20260926.json']
        run(script.removesuffix('.py'),args,env=env)
    original_f=(harness/'thread_f_original.py').read_text(encoding='utf-8')
    adapted_f=original_f.replace("PIN='"+'fa94ab3e2fdd4776d84d110f4233ba84409eb947'+"'", "PIN='"+PREVIEW+"'")
    fmethods=lambda value:[ast.dump(n) for n in ast.walk(ast.parse(value)) if isinstance(n,ast.FunctionDef)]
    check('original_F_methods_preserved',fmethods(original_f)==fmethods(adapted_f),'Only the exact commit PIN changes')
    bound_f=out/'thread_f_bound.py';bound_f.write_text(adapted_f,encoding='utf-8')
    run('original_F_regressions',[sys.executable,'-B',str(bound_f),'--repo',str(root),'--json-output',str(out/'original_F_results.json')],env=env)
    # Extract exact governed timestamp/admission state without creating authority.
    states=[]
    first=root/'docs/constraint/first_slice/ai_data_center_power_infrastructure_v1'
    unresolved={'SRC-EATON-Q1-2026-RESULTS-2026-05-05','SRC-GEV-Q2-2026-RESULTS-2026-07-22'}
    boundary=[]
    for p in first.glob('*BATCH016*OUTCOME*.json'):
        d=json.loads(p.read_text(encoding='utf-8'))
        rows=d.get('sources',[])+d.get('records',[])
        for row in rows:
            if row.get('source_id') in unresolved:
                state={k:row.get(k) for k in ['source_id','outcome_id','acquired_at','available_at','observed_at','hydra_available_at','known_at','verified_acquired_at']}
                state.update(path=p.relative_to(root).as_posix(),effective_acquisition_verification_status=row.get('acquisition_verification_status','TIMESTAMP_UNVERIFIED'))
                states.append(state)
                boundary.append(state['effective_acquisition_verification_status']=='TIMESTAMP_UNVERIFIED' and state['known_at'] is None and state['verified_acquired_at'] is None)
    check('boundary_state',len({s['source_id'] for s in states})==2 and all(boundary),states)
    save('unresolved_state.json',{'records':states,'D_OWNER_GATE':'BLOCKED','owner_gate_basis':'External governing hold; this run does not authenticate or change the owner gate.','promotion_authorized':False})
    after=snapshot(); save('source_hashes_after.json',after)
    check('source_hashes_stable',initial==after,{'changed':[p for p in initial if initial[p]!=after.get(p)]})
    final_status=git('status','--porcelain=v1'); save('final_repository_status.json',{'head':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),'status_porcelain':final_status})
    check('final_clean_status',not final_status,final_status)
    result=json.loads((out/'pytest_results.json').read_text()) if (out/'pytest_results.json').exists() else {'inventory':[],'reports':[]}
    report_rows=result['reports']
    skipped=[r for r in report_rows if r['outcome']=='skipped']
    permitted={'test_symlinked_object_tree_into_public_repo_is_rejected','test_symlinked_receipt_tree_into_public_repo_is_rejected','test_symlinked_release_tree_into_public_repo_is_rejected','test_symlinked_object_tree_outside_private_root_is_rejected'}
    for r in skipped:
        r['allowed']=r['nodeid'].split('::')[-1] in permitted and 'test_store.py::' in r['nodeid'] and 'WinError 1314' in (r.get('detail') or '')
        r['existing_condition']='constraint-t1-raw-artifact-store/tests/test_store.py:_symlink'
    save('skip_inventory.json',skipped)
    check('skip_conditions',all(r['allowed'] for r in skipped),skipped)
    if (out/'pre_execution_collection.json').exists():
        check('inventory_not_reduced',json.loads((out/'pre_execution_collection.json').read_text())==result['inventory'],{'collected':len(result['inventory'])})
    groups={}
    for name,needles in GROUPS.items():
        nodes=[n for n in result['inventory'] if any(x in n for x in needles)]
        cr=[c for c in commands if any(x in c['label'] for x in needles)]
        static=[c for c in checks if any(x in c['name'] for x in needles)]
        related=[r for r in report_rows if r['nodeid'] in nodes]
        groups[name]={'test_nodeids':nodes,'commands':[c['label'] for c in cr],'checks':static,
                      'test_report_totals':{x:sum(r['outcome']==x and (r['phase']=='call' or x!='passed') for r in related) for x in ['passed','failed','skipped']},
                      'command_pass':sum(c['exit_code']==0 for c in cr),'command_fail':sum(c['exit_code']!=0 for c in cr),
                      'status':'FAIL' if any(r['outcome']=='failed' for r in related) or any(c['exit_code'] for c in cr) or any(not c['passed'] for c in static) else ('PASS_WITH_SKIPS' if any(r['outcome']=='skipped' for r in related) else 'PASS')}
        if not nodes and not cr and not static: groups[name]['status']='NOT_COVERED'
    save('matrix.json',groups); save('checks.json',checks)
    allgood=all(c['exit_code']==0 for c in commands) and all(c['passed'] for c in checks) and all(g['status'] not in ['FAIL','NOT_COVERED'] for g in groups.values())
    summary={'result':'PASS_WITH_SKIPS' if allgood and skipped else 'PASS' if allgood else 'FAIL',
             'candidate_tree':TREE,'candidate_commit':PREVIEW,'current_main':MAIN,'pr119_head':HEAD,
             'test_count':len(result['inventory']),'test_reports':{x:sum(r['outcome']==x and (r['phase']=='call' or x!='passed') for r in report_rows) for x in ['passed','failed','skipped']},
             'command_totals':{'pass':sum(c['exit_code']==0 for c in commands),'fail':sum(c['exit_code']!=0 for c in commands)},
             'checks_failed':[c['name'] for c in checks if not c['passed']],
             'evidence_promotion':False,'canonical_status_claimed':False,'production_status_claimed':False,
             'integration_readiness_claimed':False,'regression_localization':'UNKNOWN' if not allgood else None,
             'construction_scope':'CURRENT_MAIN_PLUS_PR119_WITH_REPAIRS_ALREADY_IN_MAIN','repair_commits':REPAIRS,'original_two_input_candidate':ORIGINAL}
    calls=[r for r in report_rows if r['phase']=='call' and r['report_type']=='TestReport']
    subtests=[r for r in report_rows if r['report_type']=='SubTestReport']
    summary['test_methods']={x:sum(r['outcome']==x for r in calls) for x in ['passed','failed','skipped']}
    summary['subtests']={x:sum(r['outcome']==x for r in subtests) for x in ['passed','failed','skipped']}
    summary['changed_input_commits']=inputs['changed_input_commits']
    summary['source_file_count']=inputs['source_file_count']
    summary['previous_validation_tree']=inputs['previous_validation_tree']
    summary['original_F']=json.loads((out/'original_F_results.json').read_text())
    save('summary.json',summary)
    save('report_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='report_hashes.json'})
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if allgood else 1

if __name__=='__main__': raise SystemExit(main())

