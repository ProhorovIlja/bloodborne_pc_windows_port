"""Fail-closed original-source guard tests for native launcher file write stability."""
import importlib.util
from pathlib import Path
import unittest

src = Path(__file__).with_name("stage.py")
spec = importlib.util.spec_from_file_location("yt_atomic_stage", src)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AtomicSourceStageTests(unittest.TestCase):
    def test_only_known_original_file_and_hash(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOB, "b54974c649610bef59e53a61ae294edc2d386cda")
        self.assertEqual(m.PATH, "bbport/launcher/bbport_launcher_win.py")
        self.assertEqual(len(m.REPLACEMENTS), 6)

    def test_source_exact_one_file_insertions(self):
        source = "\n\nUNRELATED\n".join(old for old, _ in m.REPLACEMENTS)
        changed = m.patch_text(source)
        self.assertIn("def atomic_utf8_write(", changed)
        self.assertIn("os.replace(temporary, path)", changed)
        self.assertIn("out.flush()", changed)
        self.assertIn("os.fsync(out.fileno())", changed)
        self.assertIn("if path.is_symlink():", changed)
        for name in ("mods.json", "patches.json", "CONFIG_FILE", "ini_path()"):
            self.assertIn(name, changed)
        self.assertNotIn("CONFIG_FILE.write_text(", changed)
        with self.assertRaises(ValueError):
            m.patch_text(changed)

    def test_ambiguous_or_drifted_file_fails(self):
        original = "\n\nUNRELATED\n".join(old for old, _ in m.REPLACEMENTS)
        for modified in (
            original + m.REPLACEMENTS[2][0],
            original.replace("CONFIG_FILE.write_text", "CONFIG_FILE.write_bytes"),
            original.replace("ini_path().write_text", "other.write_text"),
        ):
            with self.subTest(modified=modified[-90:]):
                with self.assertRaises(ValueError):
                    m.patch_text(modified)


if __name__ == "__main__":
    unittest.main()
