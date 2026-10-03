"""Restore the immutable public C evidence archive; no HYDRA imports."""
import base64,hashlib,io,json,os,stat,sys,zipfile
from pathlib import Path,PurePosixPath

def main():
    out=Path(sys.argv[1]).resolve()
    if os.name!='nt' or out.drive.upper()!='D:':raise SystemExit('Windows D: required')
    if out.exists():raise SystemExit('C dependency destination already exists')
    here=Path(__file__).resolve().parent
    pins=json.loads((here/'freshness_inputs.json').read_text())
    data=base64.b64decode((here/'C_evidence.zip.b64').read_text().strip(),validate=True)
    if len(data)!=pins['C_archive_bytes'] or hashlib.sha256(data).hexdigest()!=pins['C_archive_sha256']:raise SystemExit('Immutable C archive mismatch')
    members=[];seen=set()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.testzip() is not None:raise SystemExit('Archive CRC failure')
        for entry in archive.infolist():
            path=PurePosixPath(entry.filename.replace('\\','/'))
            if path.is_absolute() or '..' in path.parts or any(':' in p for p in path.parts) or stat.S_ISLNK(entry.external_attr>>16):raise SystemExit('Unsafe archive member')
            key=path.as_posix().casefold()
            if key in seen:raise SystemExit('Duplicate archive member')
            seen.add(key)
            if entry.is_dir():continue
            content=archive.read(entry);members.append((path,content))
    if len(members)!=pins['C_archive_members']:raise SystemExit('Archive member count mismatch')
    for path,content in members:
        target=out.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    manifest=out/'matrix/report_hashes.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!=pins['C_manifest_sha256']:raise SystemExit('C manifest mismatch')
    record={'result':'PASS','archive_sha256':pins['C_archive_sha256'],'archive_bytes':len(data),'archive_members':len(members),'C_manifest_sha256':pins['C_manifest_sha256'],'original_C_run':pins['C_run_id'],'original_D_failure_preserved':True,'C_summary_modified':False}
    (out.parent/'C_restore_verification.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
