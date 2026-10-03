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
from report_gate import validate_execution_reports

PINS = json.loads((Path(__file__).parent/'candidate_inputs.json').read_text(encoding='utf-8'))
MAIN = PINS['main']
HEAD = PINS['pr119_head']
HEAD138 = PINS['pr138_head']
HEAD141 = PINS['pr141_head']
HEAD143 = PINS['pr143_head']
PREVIOUS_MAIN = PINS['previous_candidate_main']
PREVIOUS = PINS['previous_candidate_commit']
PREVIOUS_TREE = PINS['previous_candidate_tree']
BASE143 = PINS['pr143_merge_base']
BASE = PINS['pr119_historical_base']
BASE138 = PINS['pr138_merge_base']
PREVIEW = PINS['candidate_commit']
TREE = PINS['candidate_tree']
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
 '08_Batch034_evidence_lineage':['test_ordinary_t2_evidence_lineage','batch034_t2_evidence_lineage','batch034_builder_bytes','Batch034_rebuild','preserved_F_non_escalation'],
 '09_Constraint_V018_runtime':['constraint-runtime/tests/','test_unresolved_gates','canary_boundary_probe'],
 '10_public_repository_hygiene':['validate_public_repository','public_root_hygiene'],
 '11_governed_compile_AST':['compile_runtime','governed_ast'],
 '12_manifest_hash_validators':['nyx_validate_constraint_successor_chain','validate_constraint_t1_first_slice_attestation','validate_constraint_second_slice_batch033','validate_constraint_second_slice_batch034','validate_constraint_first_slice_custody','Batch034_rebuild','batch034_builder_bytes'],
 '13_exact_predecessor_recovery':['test_batch033_custody_continuation','test_restack_successor_binding','test_timestamp_successor_binding'],
 '14_unresolved_timestamps':['test_timestamp_gate','test_unverified_metadata_boundary','test_temporal_consistency_boundary','test_first_slice_temporal_consistency','temporal_coexistence_probe','test_pit_conservative_availability','test_constraint_first_slice_outcome_coverage_adversarial','test_unresolved_gates','canary_boundary_probe'],
 '15_authority_admission_non_elevation':['test_authority','test_native_binding_admission','test_native_admission_input_types','test_native_t5_t6_bridge','test_constraint_first_slice_acceptance_gate_adversarial','boundary_state','test_unresolved_gates','preserved_F_non_escalation','temporal_coexistence_probe','admission_held'],
}

def main():
    if os.name != 'nt':
        raise SystemExit('Windows required; no HYDRA runtime tests executed.')
    root = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
    if root.drive.upper() != 'D:' or out.drive.upper() != 'D:': raise SystemExit('Project data must be on D:')
    harness = Path(__file__).resolve().parent
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
         'pr138_head':HEAD138,'pr141_head':HEAD141,'pr143_head':HEAD143,'previous_candidate_commit':PREVIOUS,'historical_base':BASE,'runtime_execution':'HOSTED_WINDOWS_NOT_USER_WORKSTATION'})
    regression_bytes=(root/'constraint-runtime/tests/test_unresolved_gates.py').read_bytes()
    check('preserved_E_regression_bytes',hashlib.sha256(regression_bytes).hexdigest()=='a89c65bcca402ad95e94b6082d1b282f19750a1ca5b543a618b150745f91e0d5',{'source_commit':'53ac6e28cb3088bdaf5d7c2702f44f362998892f','source_path':'constraint-runtime/tests/test_unresolved_gates.py','candidate_runtime_modified':False})
    check('candidate_identity',git('rev-parse','HEAD')==PREVIEW and git('rev-parse','HEAD^{tree}')==TREE,git('show','-s','--format=%H %T %P','HEAD'))
    check('parents',git('show','-s','--format=%P','HEAD').split()==[MAIN,HEAD143],git('show','-s','--format=%P','HEAD'))
    check('initial_clean_status',not git('status','--porcelain=v1'),git('status','--porcelain=v1'))
    initial=snapshot(); save('source_hashes_before.json',initial)
    if not all(c['passed'] for c in checks):
        save('checks.json',checks); raise SystemExit('Safety precondition failed')
    # New main contains PR119; prove its composition with PR138 equals verified V001.
    previous_trees=[]
    for n in [1,2]:
        code,observed=run('reproduce_previous_tree_'+str(n),['git','merge-tree','--write-tree',MAIN,HEAD138])
        check('reproduced_previous_tree_'+str(n),code==0 and observed.strip()==PREVIOUS_TREE,observed)
        previous_trees.append(observed.strip())
    check('previous_trees_reproducible',len(set(previous_trees))==1,previous_trees)
    ancestor119=subprocess.run(['git','merge-base','--is-ancestor',HEAD,MAIN],cwd=root,capture_output=True)
    check('PR119_already_in_current_main',ancestor119.returncode==0,{'pr119_head':HEAD,'main':MAIN})
    ancestor138=subprocess.run(['git','merge-base','--is-ancestor',HEAD138,MAIN],cwd=root,capture_output=True)
    check('PR138_already_in_current_main',ancestor138.returncode==0,{'pr138_head':HEAD138,'main':MAIN})
    check('current_main_exact_verified_V001_tree',git('rev-parse',MAIN+'^{tree}')==PREVIOUS_TREE,git('rev-parse',MAIN+'^{tree}'))
    pr_paths=set(git('diff','--name-only',BASE,HEAD).splitlines())
    pr138_paths=set(git('diff','--name-only',BASE138,HEAD138).splitlines())
    check('repair_ownership_disjoint',not pr_paths.intersection(pr138_paths),sorted(pr_paths.intersection(pr138_paths)))
    ancestor=subprocess.run(['git','merge-base','--is-ancestor',HEAD141,MAIN],cwd=root,capture_output=True)
    check('PR141_already_in_main',ancestor.returncode==0,{'pr141_head':HEAD141,'main':MAIN})
    def ls(ref):
        return {line.split('\t',1)[1]:line.split('\t',1)[0] for line in git('ls-tree','-r',ref).splitlines()}
    maps={ref:ls(ref) for ref in [MAIN,HEAD,HEAD138,HEAD143,PREVIOUS,PREVIEW]}
    mismatches=[]
    for p,v in maps[PREVIOUS].items():
        expected=maps[HEAD138].get(p) if p in pr138_paths else maps[MAIN].get(p)
        if v!=expected: mismatches.append({'path':p,'actual':v,'expected':expected})
    expected_paths=(set(maps[MAIN])-pr138_paths)|(set(maps[HEAD138])&pr138_paths)
    check('exact_previous_owned_and_main_bytes',not mismatches and set(maps[PREVIOUS])==expected_paths,{'pr119_owned_paths':len(pr_paths),'pr138_owned_paths':len(pr138_paths),'previous_paths':len(maps[PREVIOUS]),'mismatches':mismatches})
    check('previous_identity',git('rev-parse',PREVIOUS+'^{tree}')==PREVIOUS_TREE,git('show','-s','--format=%H %T %P',PREVIOUS))
    check('previous_parents',git('show','-s','--format=%P',PREVIOUS).split()==[PREVIOUS_MAIN,HEAD,HEAD138],git('show','-s','--format=%P',PREVIOUS))
    pr143_paths=set(git('diff','--name-only',BASE143,HEAD143).splitlines())
    resolution_manifest=json.loads((harness/'conflict_resolution_allowlist.json').read_text(encoding='utf-8'))
    resolutions={row['path']:row for row in resolution_manifest['resolutions']}
    expected_overlap={
        'constraint-t1-raw-artifact-store/src/hydra_constraint_t1_raw/first_slice_materialization.py',
        'constraint-t1-raw-artifact-store/src/hydra_constraint_t1_raw/replay_lineage.py',
    }
    check('PR143_exact_path_inventory',pr143_paths==set(PINS['pr143_paths']) and len(pr143_paths)==8,sorted(pr143_paths))
    check('PR143_exact_production_overlap',pr_paths.intersection(pr143_paths)==expected_overlap and not pr138_paths.intersection(pr143_paths),sorted(pr_paths.intersection(pr143_paths)))
    check('resolution_allowlist_exact',len(resolution_manifest['resolutions'])==2 and set(resolutions)==expected_overlap,sorted(resolutions))
    check('resolution_input_binding',resolution_manifest['previous_candidate_commit']==PREVIOUS and resolution_manifest['pr143_head']==HEAD143,{'previous':resolution_manifest['previous_candidate_commit'],'pr143':resolution_manifest['pr143_head']})
    fixture_rows=resolution_manifest.get('fixture_adaptations',[])
    fixtures={row['path']:row for row in fixture_rows}
    fixture_path='constraint-t1-raw-artifact-store/tests/test_first_slice_temporal_consistency.py'
    check('fixture_allowlist_exact',len(fixture_rows)==1 and set(fixtures)=={fixture_path} and not set(fixtures).intersection(resolutions),sorted(fixtures))
    check('fixture_requires_observed_red',resolution_manifest.get('test_first_red',{}).get('run_id')==37142656231 and resolution_manifest.get('test_first_red',{}).get('candidate_commit')=='0390f3ae8a85d4185cdbbdd1f6f9c2ed601ea7a6',resolution_manifest.get('test_first_red'))
    original_fixture=(harness/'pr143_original_test_first_slice_temporal_consistency.py').read_bytes()
    original_blob=hashlib.sha1(b'blob '+str(len(original_fixture)).encode()+b'\0'+original_fixture).hexdigest()
    check('original_PR143_fixture_binding',original_blob=='4215eb03b1856104bf45701f2fa3b8193bd85038',original_blob)
    def fixture_methods(data):
        return {node.name:ast.dump(node,include_attributes=False) for node in ast.walk(ast.parse(data)) if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')}
    original_methods=fixture_methods(original_fixture);candidate_methods=fixture_methods((root/fixture_path).read_bytes())
    check('all_twelve_PR143_method_bodies_preserved',len(original_methods)==12 and original_methods==candidate_methods,{'original_count':len(original_methods),'candidate_count':len(candidate_methods)})
    authorized=dict(resolutions);authorized.update(fixtures)
    expected_new=dict(maps[PREVIOUS])
    for path in sorted(pr143_paths):
        if path in authorized:
            row=authorized[path]
            check('resolution_mode_'+path,row['mode']=='100644' and re.fullmatch(r'[0-9a-f]{40}',row['git_blob_sha']) is not None and re.fullmatch(r'[0-9a-f]{64}',row['sha256']) is not None,row)
            expected_new[path]=row['mode']+' blob '+row['git_blob_sha']
            check('reviewed_resolution_sha256_'+path,hashlib.sha256((root/path).read_bytes()).hexdigest()==row['sha256'],row['sha256'])
        else:
            expected_new[path]=maps[HEAD143][path]
    new_mismatches=[{'path':p,'expected':v,'actual':maps[PREVIEW].get(p)} for p,v in expected_new.items() if maps[PREVIEW].get(p)!=v]
    check('exact_PR143_and_reviewed_resolution_bytes',not new_mismatches and set(expected_new)==set(maps[PREVIEW]) and len(initial)==PINS['file_count'],{'mismatches':new_mismatches,'candidate_paths':len(initial),'exact_PR143_paths':len(pr143_paths)-len(authorized),'resolved_production_paths':len(resolutions),'reviewed_fixture_adaptations':len(fixtures)})
    save('conflict_resolution_binding.json',resolution_manifest)
    if not all(c['passed'] for c in checks):
        save('construction_check.json',checks); raise SystemExit('Resolution binding safety check failed')
    # Independent indexes reconstruct the reviewed composition without touching source files.
    for n in [1,2]:
        index=out/('reproduction_'+str(n)+'.index')
        if index.exists(): raise SystemExit('Reproduction index already exists')
        index_env=os.environ.copy();index_env['GIT_INDEX_FILE']=str(index)
        code,detail=run('PR143_index_read_'+str(n),['git','read-tree',PREVIOUS],env=index_env)
        check('PR143_index_read_'+str(n),code==0,detail)
        for ordinal,path in enumerate(sorted(pr143_paths),start=1):
            mode,kind,blob=expected_new[path].split()
            code,detail=run('PR143_index_update_'+str(n)+'_'+str(ordinal),['git','update-index','--add','--cacheinfo',mode,blob,path],env=index_env)
            check('PR143_index_update_'+str(n)+'_'+str(ordinal),code==0,{'path':path,'detail':detail})
        code,reconstructed=run('PR143_reproduce_tree_'+str(n),['git','write-tree'],env=index_env)
        check('PR143_reproduced_tree_'+str(n),code==0 and reconstructed.strip()==TREE,reconstructed)
    save('construction_check.json',checks)
    if not all(c['passed'] for c in checks): raise SystemExit('Construction safety check failed')
    inventory=[]; parsed=[]; ast_errors=[]
    selected=[p for p in initial if p.endswith('.py') and (any(p.startswith(x+'/') for x in PACKAGES) or p in ['tools/'+x for x in SCRIPTS])]
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
    env['PYTHONPYCACHEPREFIX']=str(out/'compile-cache')
    env['PYTHONDONTWRITEBYTECODE']='1'; env['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
    env['MATRIX_SOURCE_ROOT']=str(root)
    env['MATRIX_INVENTORY']=str(out/'collected_tests.json'); env['MATRIX_RESULTS']=str(out/'pytest_results.json')
    testdirs=[p+'/tests' for p in PACKAGES]
    pytest=[sys.executable,'-m','pytest','--import-mode=importlib','-p','pytest_subtests.plugin','-p','matrix_reporter','-p','no:cacheprovider']
    run('collect_all_owners',pytest+testdirs+['--collect-only','-q'],env=env)
    if (out/'collected_tests.json').exists(): (out/'pre_execution_collection.json').write_bytes((out/'collected_tests.json').read_bytes())
    run('integrated_owners',pytest+testdirs+['-vv','--tb=long','--junitxml='+str(out/'tests.xml')],env=env)
    run('compile_runtime',[sys.executable,'-m','compileall','-q','constraint-runtime/src'],env=env)
    for script in SCRIPTS:
        args=[sys.executable,'tools/'+script]
        if script=='validate_constraint_t1_first_slice_attestation.py':
            args+=['--attestation','docs/constraint/validation/HYDRA_CONSTRAINT_BATCH018_T1_NINE_SOURCE_MATERIALIZATION_ATTESTATION_V001_20260926.json']
        run(script.removesuffix('.py'),args,env=env)
    # Preserve all original F cases; reviewed PR141 now rejects the same authority input.
    original=(harness/'thread_f_original.py').read_text(encoding='utf-8')
    adapted=original.replace("PIN='fa94ab3e2fdd4776d84d110f4233ba84409eb947'", "PIN='"+PREVIEW+"'")
    def tests_ast(text):
        return [ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
    old_assertion="""            b=v.build_ordinary_t2_evidence_lineage(lineage_packet=x[1],source_records=x[0]['queue'],evidence_records=ev,expected_slice_id=v.SLICE)
            self.assertEqual(x[2],b)
            self.assertIs(b['canonical_t5_t6_admission_promoted'],False)"""
    new_assertion="""            with self.assertRaisesRegex(v.OrdinaryT2EvidenceLineageError, 'unsupported input fields'):
                v.build_ordinary_t2_evidence_lineage(lineage_packet=x[1],source_records=x[0]['queue'],evidence_records=ev,expected_slice_id=v.SLICE)"""
    check('F_exact_rejection_transition_available',adapted.count(old_assertion)==1,{'reviewed_production_PR':141,'changed_method':'test_input_authority_claim_does_not_promote_binding'})
    adapted=adapted.replace(old_assertion,new_assertion)
    original_methods={n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(original)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    adapted_methods={n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(adapted)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')}
    changed_methods=[name for name in original_methods if original_methods[name]!=adapted_methods.get(name)]
    check('F_regression_methods_preserved',set(original_methods)==set(adapted_methods) and changed_methods==['test_input_authority_claim_does_not_promote_binding'],{'methods':len(original_methods),'unchanged_methods':len(original_methods)-len(changed_methods),'changed_methods':changed_methods,'reason':'PR141 replaces unsupported-input erasure with explicit rejection; same hostile input, original retained'})
    bound=out/'thread_f_bound.py'; bound.write_text(adapted,encoding='utf-8')
    run('preserved_F_non_escalation',[sys.executable,'-B',str(bound),'--repo',str(root),'--json-output',str(out/'F_results.json')],env=env)
    run('canary_boundary_probe',[sys.executable,'-B',str(harness/'canary_boundary_probe.py'),'--repo',str(root)],env=env)
    run('temporal_coexistence_probe',[sys.executable,'-B',str(harness/'temporal_coexistence_probe.py'),'--repo',str(root),'--json-output',str(out/'temporal_coexistence_results.json')],env=env)
    binding=root/'docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_SEMICONDUCTOR_ORDINARY_T2_EVIDENCE_LINEAGE_BINDING_V001_20260928.json'
    rebuilt=out/'rebuilt_binding.json'
    run('Batch034_rebuild',[sys.executable,'-B','tools/build_constraint_second_slice_batch034_t2_evidence_lineage.py','--output',str(rebuilt)],env=env)
    check('Batch034_rebuild_exact_bytes',rebuilt.exists() and rebuilt.read_bytes()==binding.read_bytes(),{'original':hashlib.sha256(binding.read_bytes()).hexdigest(),'rebuilt':hashlib.sha256(rebuilt.read_bytes()).hexdigest() if rebuilt.exists() else None,'line_endings_only':rebuilt.exists() and rebuilt.read_bytes().replace(b'\r\n',b'\n')==binding.read_bytes().replace(b'\r\n',b'\n')})
    master=json.loads((root/'docs/constraint/architecture/HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH034_MASTER_STATUS_V001_20260928.json').read_text())
    check('admission_held',master['readiness']['SECOND_SLICE_IMPLEMENTATION_ADMITTED']['status']=='NO' and master['first_serious_constraint_run']=='BLOCKED',master['readiness'])
    # Exact governed timestamp/admission state: classification is in review records.

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
                state.update(path=p.relative_to(root).as_posix(),recorded_acquisition_verification_status=row.get('acquisition_verification_status'),review_classification='TIMESTAMP_UNVERIFIED',review_source='docs/constraint/validation/NYX_TASK6_STACKED_TEMPORAL_CLOSEOUT_20260927.md:17')
                states.append(state)
                boundary.append(state['recorded_acquisition_verification_status'] in [None,'TIMESTAMP_UNVERIFIED'] and state['known_at'] is None and state['verified_acquired_at'] is None)
    review_text=(root/'docs/constraint/validation/NYX_TASK6_STACKED_TEMPORAL_CLOSEOUT_20260927.md').read_text(encoding='utf-8')
    check('timestamp_review_classification_preserved',all(s in review_text for s in unresolved) and 'TIMESTAMP_UNVERIFIED' in review_text,'review classification retained; no source JSON field invented')
    check('boundary_state',len({s['source_id'] for s in states})==2 and all(boundary),states)
    save('unresolved_state.json',{'records':states,'D_OWNER_GATE':'BLOCKED','owner_gate_basis':'External governing hold; this run does not authenticate or change the owner gate.','promotion_authorized':False})
    after=snapshot(); save('source_hashes_after.json',after)
    check('source_hashes_stable',initial==after,{'changed':[p for p in initial if initial[p]!=after.get(p)]})
    final_status=git('status','--porcelain=v1'); save('final_repository_status.json',{'head':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),'status_porcelain':final_status})
    check('final_clean_status',not final_status,final_status)
    result=json.loads((out/'pytest_results.json').read_text()) if (out/'pytest_results.json').exists() else {'inventory':[],'reports':[]}
    report_rows=result['reports']
    method_rows=[r for r in report_rows if r['report_type']=='TestReport']
    source_map=result.get('source_map',{})
    check('all_test_sources_recorded',set(source_map)==set(result['inventory']) and len(source_map)==PINS['expected_native_test_methods'],{'sources':len(source_map),'collected':len(result['inventory']),'expected_from_preserved_inventory_and_added_methods':PINS['expected_native_test_methods']})
    subtest_rows=[r for r in report_rows if r['report_type']=='SubTestReport']
    skipped=[r for r in report_rows if r['outcome']=='skipped']
    permitted={'test_symlinked_object_tree_into_public_repo_is_rejected','test_symlinked_receipt_tree_into_public_repo_is_rejected','test_symlinked_release_tree_into_public_repo_is_rejected','test_symlinked_object_tree_outside_private_root_is_rejected'}
    for r in skipped:
        r['allowed']=r['nodeid'].split('::')[-1] in permitted and 'WinError 1314' in (r.get('detail') or '')
        r['existing_condition']='constraint-t1-raw-artifact-store/tests/test_store.py:_symlink_or_skip'
    save('skip_inventory.json',skipped)
    check('skip_conditions',all(r['allowed'] for r in skipped),skipped)
    execution_errors=validate_execution_reports(result,expected_count=PINS['expected_native_test_methods'],permitted_skip_methods=permitted)
    check('execution_reports_complete',not execution_errors,{'errors':execution_errors,'expected_native_methods':PINS['expected_native_test_methods'],'session_exitstatus':result.get('exitstatus')})
    if (out/'pre_execution_collection.json').exists():
        check('inventory_not_reduced',json.loads((out/'pre_execution_collection.json').read_text())==result['inventory'],{'collected':len(result['inventory'])})
    groups={}
    for name,needles in GROUPS.items():
        nodes=[n for n in result['inventory'] if any(x in n or x in source_map.get(n,{}).get('path','') for x in needles)]
        cr=[c for c in commands if any(x in c['label'] for x in needles)]
        static=[c for c in checks if any(x in c['name'] for x in needles)]
        related=[r for r in report_rows if r['nodeid'] in nodes]
        groups[name]={'test_nodeids':nodes,'commands':[c['label'] for c in cr],'checks':static,
                      'test_method_totals':{x:sum(r['outcome']==x and r['report_type']=='TestReport' and (r['phase']=='call' or x!='passed') for r in related) for x in ['passed','failed','skipped']},
                      'subtest_totals':{x:sum(r['outcome']==x and r['report_type']=='SubTestReport' for r in related) for x in ['passed','failed','skipped']},
                      'command_pass':sum(c['exit_code']==0 for c in cr),'command_fail':sum(c['exit_code']!=0 for c in cr),
                      'status':'FAIL' if any(r['outcome']=='failed' for r in related) or any(c['exit_code'] for c in cr) or any(not c['passed'] for c in static) else ('PASS_WITH_ALLOWED_SKIPS' if any(r['outcome']=='skipped' for r in related) else 'PASS')}
        if not nodes and not cr and not static: groups[name]['status']='NOT_COVERED'
    save('matrix.json',groups); save('checks.json',checks)
    allgood=all(c['exit_code']==0 for c in commands) and all(c['passed'] for c in checks) and all(g['status'] not in ['FAIL','NOT_COVERED'] for g in groups.values())
    summary={'result':'PASS_WITH_ALLOWED_SKIPS' if allgood and skipped else 'PASS' if allgood else 'FAIL',
             'candidate_tree':TREE,'candidate_commit':PREVIEW,'current_main':MAIN,'pr119_head':HEAD,
             'test_count':len(result['inventory']),'test_reports':{x:sum(r['outcome']==x and (r['phase']=='call' or x!='passed') for r in method_rows) for x in ['passed','failed','skipped']},
             'subtest_reports':{x:sum(r['outcome']==x for r in subtest_rows) for x in ['passed','failed','skipped']},
             'command_totals':{'pass':sum(c['exit_code']==0 for c in commands),'fail':sum(c['exit_code']!=0 for c in commands)},
             'checks_failed':[c['name'] for c in checks if not c['passed']],
             'evidence_records_mutated':False,'canonical_status_claimed':False,'production_status_claimed':False,
             'integration_readiness_claimed':False,'regression_localization':'UNKNOWN' if not allgood else None,
             'Thread_B_handoff':'PASS independently reproduced and inventoried',
             'pr138_head':HEAD138,'pr141_head':HEAD141,'pr143_head':HEAD143,'previous_candidate_commit':PREVIOUS,'scope':'EXACT_CURRENT_MAIN_PLUS_PR143_WITH_TWO_PRODUCTION_RESOLUTIONS_AND_TEST_FIRST_FIXTURE_ADAPTATION',
             'thread_D_V006':'BLOCKED_BY_THREAD_C' if not allgood else 'ELIGIBLE_FOR_CHANGED_TREE_VALIDATION'}
    save('summary.json',summary)
    save('report_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='report_hashes.json'})
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if allgood else 1

if __name__=='__main__': raise SystemExit(main())
