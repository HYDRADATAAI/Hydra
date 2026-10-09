from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "aws-market-data-deploy.yml"
STEP_NAME = "Empty versioned buckets and delete stack"


def teardown_script() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = lines.index(f"      - name: {STEP_NAME}")
    run_line = next(i for i in range(start + 1, len(lines)) if lines[i] == "        run: |")
    body = []
    for line in lines[run_line + 1:]:
        if line.strip() and len(line) - len(line.lstrip(" ")) <= 8:
            break
        body.append(line[10:] if line.startswith("          ") else "")
    return "\n".join(body) + "\n"


@unittest.skipUnless(shutil.which("bash"), "the deploy teardown workflow uses Bash")
class DeployTeardownOwnershipTests(unittest.TestCase):
    def test_mismatched_run_tag_stops_before_bucket_cleanup_or_stack_delete(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            aws_log = root / "aws-calls.jsonl"
            sam_log = root / "sam-calls.jsonl"

            aws = root / "aws"
            aws.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "args = sys.argv[1:]\n"
                "with open(os.environ['AWS_CALL_LOG'], 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(args) + '\\n')\n"
                "if args[:2] == ['cloudformation', 'describe-stacks']:\n"
                "    print(json.dumps({'Stacks': [{'Tags': [{'Key': 'hydra:deployment-run', 'Value': 'another-run'}], 'StackStatus': 'CREATE_COMPLETE'}]}))\n"
                "    raise SystemExit(0)\n"
                "raise SystemExit(99)\n",
                encoding="utf-8",
            )
            jq = root / "jq"
            jq.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "query = sys.argv[-1]\n"
                "data = json.load(sys.stdin)\n"
                "if 'Tags[]?' in query:\n"
                "    for tag in data['Stacks'][0].get('Tags', []):\n"
                "        if tag.get('Key') == 'hydra:deployment-run':\n"
                "            print(tag.get('Value', ''))\n"
                "    raise SystemExit(0)\n"
                "raise SystemExit(2)\n",
                encoding="utf-8",
            )
            sam = root / "sam"
            sam.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "with open(os.environ['SAM_CALL_LOG'], 'a', encoding='utf-8') as f:\n"
                "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n",
                encoding="utf-8",
            )
            for executable in (aws, jq, sam):
                executable.chmod(0o755)

            env = os.environ.copy()
            env.update({
                "AWS_CALL_LOG": str(aws_log),
                "SAM_CALL_LOG": str(sam_log),
                "AWS_REGION": "us-east-1",
                "STACK_NAME": "hydra-public-market-pipeline-demo-123-1",
                "DEPLOYMENT_RUN_TOKEN": "123-1",
                "RAW_BUCKET": "hydra-public-raw-expected",
                "CURATED_BUCKET": "hydra-public-curated-expected",
                "PATH": str(root) + os.pathsep + env.get("PATH", ""),
            })
            result = subprocess.run(
                ["bash", "-e", "-c", teardown_script()],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ownership tag does not match", result.stderr)
            calls = [json.loads(line) for line in aws_log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][:2], ["cloudformation", "describe-stacks"])
            self.assertFalse(sam_log.exists())


if __name__ == "__main__":
    unittest.main()
