"""Actual process-level localhost smoke and crash-report coverage."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("smoke_python_backend.py")
spec = importlib.util.spec_from_file_location("shyt_yt_smoke_v43", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = smoke
spec.loader.exec_module(smoke)


STANDIN = '''
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import argparse
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok" if self.path == "/status" else b"ss.info payload"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_POST(self):
        body = b'{"MessageId":"LoginResponse","Result":0}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
p = argparse.ArgumentParser()
p.add_argument("--address")
p.add_argument("--port", type=int)
opts = p.parse_args()
ThreadingHTTPServer(("127.0.0.1", opts.port), Handler).serve_forever()
'''


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.backend = Path(self.tmp.name) / "backend.py"

    def test_reference_probe_checks_all_real_endpoints(self):
        self.backend.write_text(STANDIN, encoding="utf-8")
        replies = smoke.exercise(self.backend, timeout=4)
        self.assertEqual(replies, [
            ("GET", "/status", 200),
            ("GET", "/bb-eu/ss.info", 200),
            ("POST", "/login", 200),
        ])

    def test_backend_crash_is_not_treated_as_pass_and_root_cause_is_visible(self):
        self.backend.write_text("import sys\nprint('SHYT_REFERENCE_STUB_CRASH', file=sys.stderr)\nraise RuntimeError('mock crash')\n",
                                encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(smoke.BackendSmokeFailure):
            smoke.exercise(self.backend, timeout=3)
        self.assertIn("SHYT_REFERENCE_STUB_CRASH", stderr.getvalue())
        self.assertIn("SHYT_REFERENCE_BACKEND_DIAGNOSTICS_BEGIN", stderr.getvalue())

    def test_missing_script_and_unsafe_timeouts_fail(self):
        with self.assertRaisesRegex(smoke.BackendSmokeFailure, "missing"):
            smoke.exercise(self.backend, timeout=3)
        self.backend.write_text(STANDIN, encoding="utf-8")
        with self.assertRaises(ValueError):
            smoke.exercise(self.backend, timeout=0)


if __name__ == "__main__":
    unittest.main()
