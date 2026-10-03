"""Run the twelve unchanged PR143 first-slice methods on hosted Windows.

An actual red result remains a failed workflow. No skip or result rewriting.
"""
from __future__ import annotations
import ast, hashlib, importlib.util, json, os, platform, subprocess, sys, unittest
from pathlib import Path


def main():
    if os.name!='nt':raise SystemExit('Windows required; no HYDRA imported')
    root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
    if root.drive.upper()!='D:' or out.drive.upper()!='D:':raise SystemExit('D: project and output required')
    out.mkdir(parents=True,exist_ok=True);sys.dont_write_bytecode=True
    pins=json.loads((Path(__file__).parent/'red_candidate_inputs.json').read_text())
    def save(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    def git(*args):
        p=subprocess.run(['git','-C',str(root),*args],text=True,capture_output=True)
        if p.returncode:raise RuntimeError(p.stderr)
        return p.stdout.strip()
    def state():return {'head':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),'status':git('status','--porcelain=v1','--untracked-files=all')}
    def snapshot():return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in git('ls-files').splitlines()}
    checks=[];before=None;rows=[]
    def check(name,ok,detail=None):
        checks.append({'name':name,'passed':bool(ok),'detail':detail});save('checks.json',checks)
        if not ok:raise RuntimeError(name)
    summary={'result':'FAIL','purpose':'TEST_FIRST_DIAGNOSTIC_UNCHANGED_PR143_METHODS','pins':pins,'hosted_windows':True,'user_workstation_tested':False,'canonical_admission_claimed':False,'historical_proof_claimed':False}
    try:
        save('environment.json',{'python':sys.version,'platform':platform.platform(),'github_run_id':os.environ.get('GITHUB_RUN_ID'),'source':str(root),'output':str(out),'TEMP':os.environ.get('TEMP'),'TMP':os.environ.get('TMP')})
        initial=state();save('initial_repository_status.json',initial)
        check('exact_candidate_identity',initial=={'head':pins['candidate_commit'],'tree':pins['candidate_tree'],'status':''},initial)
        check('exact_candidate_parents',git('show','-s','--format=%P','HEAD').split()==pins['parents'])
        before=snapshot();save('source_hashes_before.json',before)
        check('source_count',len(before)==pins['file_count'],len(before))
        test_path=root/pins['test_path'];test_bytes=test_path.read_bytes()
        test_blob=hashlib.sha1(b'blob '+str(len(test_bytes)).encode()+b'\0'+test_bytes).hexdigest()
        check('unchanged_PR143_test_bytes',test_blob==pins['test_git_blob_sha'] and hashlib.sha256(test_bytes).hexdigest()==pins['test_sha256'],{'git_blob_sha':test_blob,'sha256':hashlib.sha256(test_bytes).hexdigest()})
        methods=sorted(n.name for n in ast.walk(ast.parse(test_bytes)) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_'))
        check('twelve_original_method_names',methods==sorted(pins['method_names']) and len(methods)==12,methods)
        sys.path.insert(0,str(root/'constraint-t1-raw-artifact-store/src'))
        spec=importlib.util.spec_from_file_location('pr143_first_slice_temporal_consistency',test_path)
        module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
        suite=unittest.defaultTestLoader.loadTestsFromModule(module)
        check('twelve_loaded_methods',suite.countTestCases()==12,suite.countTestCases())
        class Result(unittest.TextTestResult):
            def addSuccess(self,test):
                super().addSuccess(test);rows.append({'nodeid':test.id(),'outcome':'passed'})
            def addFailure(self,test,err):
                super().addFailure(test,err);rows.append({'nodeid':test.id(),'outcome':'failed','traceback':self._exc_info_to_string(err,test)})
            def addError(self,test,err):
                super().addError(test,err);rows.append({'nodeid':test.id(),'outcome':'error','traceback':self._exc_info_to_string(err,test)})
            def addSkip(self,test,reason):
                super().addSkip(test,reason);rows.append({'nodeid':test.id(),'outcome':'skipped','reason':reason})
        with (out/'full_tracebacks.log').open('w',encoding='utf-8') as stream:
            result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
        save('test_results.json',{'tests_run':result.testsRun,'successful':result.wasSuccessful(),'reports':rows,'failures':[(str(t),trace) for t,trace in result.failures],'errors':[(str(t),trace) for t,trace in result.errors],'skipped':[(str(t),why) for t,why in result.skipped]})
        check('all_twelve_executed',result.testsRun==12 and len(rows)==12 and len({r['nodeid'] for r in rows})==12,{'tests_run':result.testsRun,'reports':len(rows)})
        check('no_skips',not result.skipped,result.skipped)
        imported={name:mod.__file__ for name,mod in sys.modules.items() if name.startswith('hydra_constraint_t1_raw') and getattr(mod,'__file__',None)}
        save('imported_source_modules.json',imported)
        check('all_HYDRA_imports_from_pinned_source',all(Path(p).resolve().is_relative_to(root) for p in imported.values()),imported)
        summary.update(result='PASS' if result.wasSuccessful() else 'FAIL',tests_run=result.testsRun,passed=sum(r['outcome']=='passed' for r in rows),failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped))
    except Exception as exc:
        summary['harness_error']=repr(exc)
    finally:
        try:
            after=snapshot();save('source_hashes_after.json',after);final=state();save('final_repository_status.json',final)
            stable=before is not None and before==after;clean=final=={'head':pins['candidate_commit'],'tree':pins['candidate_tree'],'status':''}
            checks.append({'name':'source_hashes_stable','passed':stable,'detail':{'count':len(after)}})
            checks.append({'name':'final_identity_clean','passed':clean,'detail':final})
            if not stable or not clean:summary['result']='FAIL'
        except Exception as exc:summary.update(result='FAIL',final_verification_error=repr(exc))
        summary['failed_harness_checks']=[x['name'] for x in checks if not x['passed']]
        save('checks.json',checks);save('summary.json',summary)
        save('report_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='report_hashes.json'})
        print(json.dumps(summary,indent=2),flush=True)
    return 0 if summary['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
