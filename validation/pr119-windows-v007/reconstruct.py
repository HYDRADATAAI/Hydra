"""Reproduce current main plus PR119 in two path orders; no source mutations."""
import json,os,subprocess,sys
from pathlib import Path

def main():
    root,out,order=Path(sys.argv[1]),Path(sys.argv[2]),int(sys.argv[3])
    pins=json.loads((Path(__file__).parent/'candidate_inputs.json').read_text())
    records=[]
    def git(*args,env=None,data=None):
        cmd=['git','-C',str(root),*args]
        p=subprocess.run(cmd,input=None if data is None else data.encode('utf-8'),capture_output=True,env=env)
        stdout=p.stdout.decode('utf-8');stderr=p.stderr.decode('utf-8')
        records.append({'argv':cmd,'cwd':str(Path.cwd()),'stdin':data,'stdin_encoding':'UTF-8, LF, no newline translation','exit_code':p.returncode,'stdout':stdout,'stderr':stderr,'GIT_INDEX_FILE':(env or os.environ).get('GIT_INDEX_FILE')})
        (out/f'reconstruction_{order}_commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
        if p.returncode:raise RuntimeError(stderr)
        return stdout.strip()
    def ls(ref):return {s.split('\t',1)[1]:s.split('\t',1)[0] for s in git('ls-tree','-r',ref).splitlines()}
    def changed(a,b):return {p for p in set(a)|set(b) if a.get(p)!=b.get(p)}
    mainmap=ls(pins['main']);headmap=ls(pins['pr119_head']);base=ls('bf74ad8352cc8681b374e185772085212619f00f');actual=ls(pins['candidate_commit'])
    pr=changed(base,headmap);mainchanges=changed(base,mainmap)
    assert not pr&mainchanges,'Unexpected changed-path overlap'
    expected=dict(mainmap)
    for path in pr:
        if path in headmap:expected[path]=headmap[path]
        else:expected.pop(path,None)
    assert expected==actual,'Missing, mutated, or third-state path'
    assert len(actual)==pins['source_file_count']
    assert git('merge-tree','--write-tree',pins['main'],pins['pr119_head'])==pins['candidate_tree']
    assert git('show','-s','--format=%P',pins['candidate_commit']).split()==[pins['main'],pins['pr119_head']]
    index=out/f'reconstruction_{order}.index'
    if index.exists():raise RuntimeError('Temporary index already exists')
    env=os.environ.copy();env['GIT_INDEX_FILE']=str(index.resolve())
    git('read-tree',pins['main'],env=env)
    rows=[]
    for path in sorted(pr,reverse=order==2):
        if path in headmap:
            mode,kind,digest=headmap[path].split();assert kind=='blob'
            rows.append(f'{mode} {digest}\t{path}\n')
        else:rows.append('0 '+'0'*40+'\t'+path+'\n')
    git('update-index','--index-info',env=env,data=''.join(rows))
    reproduced=git('write-tree',env=env);index.unlink()
    assert reproduced==pins['candidate_tree']
    old=ls(pins['previous_validation_candidate']);drift=sorted(changed(old,actual))
    result={'passed':True,'inputs':pins,'order':order,'tree':reproduced,'candidate_files':len(actual),'PR119_owned':len(pr),'unrelated_main_paths':len(set(mainmap)-pr),'unresolved_conflicts':0,'third_state_files':[],'changed_paths_since_V006':drift,'commands':records}
    (out/f'reconstruction_{order}.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(reproduced)

if __name__=='__main__':main()
