"""Windows backported launcher must not persist secret command line arguments.

The original upstream #433 patch logs sys.argv[1:] as metadata. Those values
may contain game paths or private connection tokens on a future CLI. Keep the
local traceback useful without putting raw arguments into a persistent file.
"""
import tempfile
from pathlib import Path
from unittest import mock
import unittest
import bbport_launcher_win as launcher


class StartupLogPrivacyTests(unittest.TestCase):
    def test_does_not_copy_raw_launcher_arguments_into_persistent_log(self):
        sentinel = "SECRET_ARG_SHOULD_NOT_BE_IN_LAUNCHER_LOG"
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(launcher, "DATA_DIR", Path(folder)), \
                 mock.patch("sys.argv", ["BLauncher.exe", "--script", sentinel]):
                logfile = launcher.record_startup_failure(
                    "RuntimeError: demonstrative failure")
            self.assertIsNotNone(logfile)
            content = logfile.read_text(encoding="utf-8")
            self.assertIn("RuntimeError: demonstrative failure", content)
            self.assertNotIn(sentinel, content)
            self.assertIn("command-line arguments withheld", content)


if __name__ == "__main__":
    unittest.main()
