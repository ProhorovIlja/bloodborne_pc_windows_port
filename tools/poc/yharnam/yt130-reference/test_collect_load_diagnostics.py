"""No secret leakage or arbitrary-folder access from synthetic log collection."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util
import unittest

SCRIPT=Path(__file__).with_name("collect_load_diagnostics.py")
spec=importlib.util.spec_from_file_location("load_logs",SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class LoadLogTests(unittest.TestCase):
    def test_requires_literal_ephemeral_folder_and_log_files(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            wrong=root/"run.stderr"
            wrong.write_text("server folder: /etc\n")
            with self.assertRaisesRegex(ValueError,"Expected one isolated"):
                m.collect(wrong)

    def test_redacts_session_secrets(self):
        self.assertEqual(m.SENSITIVE.sub(r"\1\2[REDACTED]",
                         "token=abc password=xyz secret: Qwerty"),
                         "token=[REDACTED] password=[REDACTED] secret: [REDACTED]")
if __name__=="__main__":
    unittest.main()
