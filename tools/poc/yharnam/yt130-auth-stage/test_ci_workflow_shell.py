"""Fail fast on actual Bash syntax in the expensive Qt CTest workflow step.

The original 821-step Qt build passed, but CTest didn't start because a
single quoted regex was missing its closing quote. Detect that in preflight.
"""
from __future__ import annotations
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
WORKFLOW = ROOT / ".github/workflows/shyt-yt130-auth-qt-staging.yml"
STEP = "      - name: Run actual SQLite plus network protocol, admission and gameplay regressions"


def extract_bash() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    if text.count(STEP) != 1:
        raise ValueError("Qt CTest workflow step missing/duplicated")
    block = text.split(STEP, 1)[1]
    match = re.search(r"(?m)^        run: \|[ \t]*$", block)
    if not match or not re.search(r"(?m)^        shell: bash[ \t]*$", block[:match.start()]):
        raise ValueError("Qt tests must be a YAML block using real Bash")
    lines = []
    for line in block[match.end():].splitlines():
        if line and not line.startswith("          "):
            break
        if line.startswith("          "):
            lines.append(line[10:])
        elif not line:
            lines.append("")
    if not lines:
        raise ValueError("Empty Qt CTest Bash step")
    return "\n".join(lines) + "\n"


class NativeQtCIWorkflowShell(unittest.TestCase):
    def test_bash_syntax_checked_before_eleven_real_cpp_tests(self):
        body = extract_bash()
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("Bash unavailable on test runner")
        result = subprocess.run([bash, "-n"], input=body, text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ctest --test-dir", body)
        self.assertIn("SHYT_YT130_REAL_QT_NETWORK_WORLD_AND_ACCOUNT_MATRIX_PASS", body)
        self.assertIn("stream_extractor)$'", body)
        self.assertIn("accounts|server_link|admission|region|packet_routes", body)


    def test_all_expensive_bash_steps_are_syntax_checked(self):
        raw=WORKFLOW.read_text(encoding="utf-8")
        bash=shutil.which("bash")
        if bash is None:
            self.skipTest("Bash unavailable")
        blocks=re.split(r"(?m)^      - name: ",raw)[1:]
        checked=0
        for item in blocks:
            if not re.search(r"(?m)^        shell: bash[ \t]*$",item):
                continue
            run=re.search(r"(?m)^        run: \|[ \t]*$",item)
            self.assertIsNotNone(run)
            lines=[]
            for line in item[run.end():].splitlines():
                if line and not line.startswith("          "):
                    break
                lines.append(line[10:] if line.startswith("          ") else "")
            script="\n".join(lines)+"\n"
            check=subprocess.run([bash,"-n"],input=script,text=True,capture_output=True,timeout=15)
            with self.subTest(step=item.splitlines()[0]):
                self.assertEqual(check.returncode,0,check.stderr)
            checked+=1
        self.assertGreaterEqual(checked,4)


if __name__ == "__main__":
    unittest.main()
