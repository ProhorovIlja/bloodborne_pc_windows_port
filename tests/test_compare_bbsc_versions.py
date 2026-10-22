"""Byte-accurate CLS BBSC 0.0.2/native parity checks, synthetic files only."""
from pathlib import Path
import tempfile
import unittest

from tools.interop.compare_bbsc_versions import COMPONENTS, OFFICIAL, NATIVE, compare


class ParityTests(unittest.TestCase):
    def test_identical_changed_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, b = root / "official", root / "native"
            (a / OFFICIAL).mkdir(parents=True)
            (b / NATIVE).mkdir(parents=True)
            for item in COMPONENTS:
                (a / OFFICIAL / item).write_bytes(b"same")
                (b / NATIVE / item).write_bytes(b"same")
            x = compare(a, b)
            self.assertEqual(x["summary"]["identical"], len(COMPONENTS))
            (b / NATIVE / COMPONENTS[0]).write_bytes(b"new")
            x = compare(a, b)
            self.assertEqual(x["summary"]["different"], 1)
            self.assertNotEqual(x["components"][0]["official"]["sha256"],
                                x["components"][0]["native"]["sha256"])
            (b / NATIVE / COMPONENTS[1]).unlink()
            x = compare(a, b)
            self.assertEqual(x["summary"]["missing"], 1)

    def test_missing_tree(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                compare(Path(d) / "none", Path(d) / "other")


if __name__ == "__main__":
    unittest.main()
