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
            self.assertEqual(x["full_inventory"]["counts"]["shared"], len(COMPONENTS))
            self.assertEqual(x["full_inventory"]["counts"]["changed"], 0)
            self.assertFalse(x["full_inventory"]["protocol_compatibility_proven"])
            (b / NATIVE / COMPONENTS[0]).write_bytes(b"new")
            x = compare(a, b)
            self.assertEqual(x["summary"]["different"], 1)
            self.assertEqual(x["full_inventory"]["counts"]["changed"], 1)
            self.assertEqual(x["full_inventory"]["changed"][0]["path"], COMPONENTS[0])
            self.assertNotEqual(x["components"][0]["official"]["sha256"],
                                x["components"][0]["native"]["sha256"])
            (b / NATIVE / COMPONENTS[1]).unlink()
            x = compare(a, b)
            self.assertEqual(x["summary"]["missing"], 1)

    def test_full_inventory_finds_unsampled_gameplay_and_port_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, b = root / "official", root / "native"
            (a / OFFICIAL / "new").mkdir(parents=True)
            (b / NATIVE / "new").mkdir(parents=True)
            for name in COMPONENTS:
                (a / OFFICIAL / name).write_bytes(b"old")
                (b / NATIVE / name).write_bytes(b"old")
            (a / OFFICIAL / "new" / "game_event.inc").write_bytes(b"original")
            (b / NATIVE / "new" / "game_event.inc").write_bytes(b"changed script")
            (a / OFFICIAL / "bbsc_legacy_only.cpp").write_bytes(b"legacy")
            (b / NATIVE / "bbsc_native_only.cpp").write_bytes(b"native")
            (a / OFFICIAL / "save_data.json").write_text('{"secret":"do not report"}')
            x = compare(a, b)
            report = x["full_inventory"]
            self.assertEqual(report["counts"]["shared"], len(COMPONENTS)+1)
            self.assertEqual(report["counts"]["changed"], 1)
            self.assertEqual(report["changed"][0]["path"], "new/bbsc_game_event.inc")
            self.assertEqual(report["counts"]["official_only"], 1)
            self.assertEqual(report["counts"]["native_only"], 1)
            self.assertNotIn("secret", str(report))
            self.assertFalse(report["protocol_compatibility_proven"])

    def test_reject_win32_case_collision(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, b = root / "official", root / "native"
            (a / OFFICIAL).mkdir(parents=True)
            (b / NATIVE).mkdir(parents=True)
            for name in COMPONENTS:
                (a / OFFICIAL / name).write_bytes(b"x")
                (b / NATIVE / name).write_bytes(b"x")
            (a / OFFICIAL / "BBSC_NAME.cpp").write_bytes(b"a")
            (a / OFFICIAL / "bbsc_name.cpp").write_bytes(b"b")
            with self.assertRaisesRegex(ValueError,"case-colliding"):
                compare(a,b)

    def test_missing_tree(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                compare(Path(d) / "none", Path(d) / "other")


if __name__ == "__main__":
    unittest.main()
