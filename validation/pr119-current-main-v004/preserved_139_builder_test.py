"""Preserve the superseded PR139 regression body against the current candidate."""
import importlib.util,os,subprocess,sys,tempfile,unittest
from pathlib import Path
if os.name!='nt':raise SystemExit('Windows required')
ROOT=Path(os.environ['MATRIX_SOURCE_ROOT']).resolve()
spec=importlib.util.spec_from_file_location('current_batch034_validator',ROOT/'tools/validate_constraint_second_slice_batch034_t2_evidence_lineage.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
class PreservedPR139(unittest.TestCase):
    def test_builder_reproduces_canonical_git_bytes(self):
        expected=subprocess.check_output(
            ["git","show",f"HEAD:{v.BINDING.relative_to(ROOT).as_posix()}"],cwd=ROOT,
        )
        with tempfile.TemporaryDirectory(prefix="b034-exact-") as tmp:
            output=Path(tmp)/"binding.json"
            result=subprocess.run(
                [sys.executable,"-B",str(v.BUILDER),"--output",str(output)],
                cwd=ROOT,text=True,capture_output=True,timeout=60,
            )
            self.assertEqual(0,result.returncode,result.stdout+result.stderr)
            actual=output.read_bytes()
            self.assertEqual(expected,actual,"builder output must match canonical Git bytes without newline normalization")

if __name__=='__main__':unittest.main()
