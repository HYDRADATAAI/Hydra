"""Reconstruct the explicit repaired Git tree without changing tracked files."""
import hashlib, json, os, subprocess, sys
from pathlib import Path

def main():
    root, out, order = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])
    pins=json.loads((Path(__file__).parent/'candidate_inputs.json').read_text())
    records=[]
    def git(*args, env=None, data=None):
        cmd=['git','-C',str(root),*args]
        p=subprocess.run(cmd,input=data,text=True,capture_output=True,env=env)
        records.append({'argv':cmd,'cwd':str(Path.cwd()),'stdin':data,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'GIT_INDEX_FILE':(env or os.environ).get('GIT_INDEX_FILE')})
        if p.returncode: raise RuntimeError(p.stderr)
        return p.stdout.strip()
    def ls(ref):
        return {s.split('\t',1)[1]:s.split('\t',1)[0] for s in git('ls-tree','-r',ref).splitlines()}
    def changes(a,b):return {p for p in set(a)|set(b) if a.get(p)!=b.get(p)}
    def apply(target, source, paths):
        for p in paths:
            if p in source:target[p]=source[p]
            else:target.pop(p,None)
    mainmap=ls(pins['main']); headmap=ls(pins['pr119_head'])
    base=ls('bf74ad8352cc8681b374e185772085212619f00f')
    original=ls(pins['original_candidate_commit']); actual=ls(pins['candidate_commit'])
    pr=changes(base,headmap); main_changes=changes(base,mainmap)
    assert not pr&main_changes, 'Unexpected PR/main overlap'
    expected_original=dict(mainmap);apply(expected_original,headmap,pr)
    assert expected_original==original
    assert git('merge-tree','--write-tree',pins['main'],pins['pr119_head'])==pins['original_candidate_tree']
    repairs=[]; owned=set(pr)
    for key in ['repair_E','repair_F']:
        repair=ls(pins[key]); paths=changes(mainmap,repair)
        assert not owned&paths,'Unexpected repair overlap'
        owned.update(paths);repairs.append((key,repair,paths))
    expected=dict(expected_original)
    for key,repair,paths in repairs:apply(expected,repair,paths)
    declared={e['path']:e['mode']+' '+e['type']+' '+e['sha'] for e in pins['entries']}
    repair_union={p:repair[p] for _,repair,paths in repairs for p in paths}
    assert declared==repair_union,'Repair inventory drift'
    assert expected==actual,'Missing or third-state file'
    index=out/('reconstruction_'+str(order)+'.index')
    if index.exists():raise RuntimeError('Temporary index already exists')
    env=os.environ.copy();env['GIT_INDEX_FILE']=str(index.resolve())
    git('read-tree',pins['main'],env=env)
    stages=[('PR119',headmap,pr),*repairs]
    if order==2:stages=list(reversed(stages))
    for _,mapping,paths in stages:
        rows=[]
        for p in sorted(paths,reverse=order==2):
            if p in mapping:
                mode,kind,digest=mapping[p].split()
                rows.append(f'{mode} {digest}\t{p}\n')
            else:rows.append('0 '+'0'*40+'\t'+p+'\n')
        git('update-index','--index-info',env=env,data=''.join(rows))
    reproduced=git('write-tree',env=env)
    index.unlink()
    assert reproduced==pins['candidate_tree']
    result={'passed':True,'inputs':pins,'order':order,'tree':reproduced,'candidate_files':len(actual),'PR119_owned':len(pr),'E_owned':len(repairs[0][2]),'F_owned':len(repairs[1][2]),'unrelated_main_paths':len(set(mainmap)-owned),'unresolved_conflicts':0,'third_state_files':[],'commands':records}
    (out/f'reconstruction_{order}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(reproduced)

if __name__=='__main__':main()
