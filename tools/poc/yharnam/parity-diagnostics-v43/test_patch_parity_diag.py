"""Tests for fail-closed diagnostics on the pinned reference backend."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).with_name("patch_parity_diag.py")
spec = importlib.util.spec_from_file_location("shyt_v43_parity_diag", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


TEST_SOURCE = '''import http.client
import os
import subprocess
import sys
class Server:
    def __init__(self, kind, workdir):
        if kind == "python":
            self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            self.log = open(os.path.join(workdir, "shadnet.log"), "wb")
    def send(self):
        resp = conn.getresponse()
        return resp
    def stop(self):
        if getattr(self, "log", None):
            self.log.close()
'''


class DiagnosticTests(unittest.TestCase):
    def test_stderr_capture_and_disconnect_context(self):
        changed = module.transform(TEST_SOURCE)
        self.assertIn('self.log = open(os.path.join(workdir, "python-backend.log"), "wb")', changed)
        self.assertIn('stderr=subprocess.STDOUT', changed)
        self.assertIn('except (OSError, http.client.HTTPException)', changed)
        self.assertIn('SHYT_PARITY_PYTHON_REFERENCE_FAILURE', changed)
        self.assertIn('raise\n        return resp', changed)
        compile(changed, "<parity diagnostics>", "exec")

    def test_applies_exactly_once_and_never_changes_parity_assertions(self):
        once = module.transform(TEST_SOURCE)
        with self.assertRaisesRegex(ValueError, "already patched"):
            module.transform(once)
        with self.assertRaisesRegex(ValueError, "pinned upstream parity test changed"):
            module.transform(TEST_SOURCE.replace("resp = conn.getresponse()", "resp = conn.read()"))
        with self.assertRaisesRegex(ValueError, "cleanup anchor"):
            module.transform(TEST_SOURCE.replace('"shadnet.log"', '"other.log"'))


if __name__ == "__main__":
    unittest.main()
