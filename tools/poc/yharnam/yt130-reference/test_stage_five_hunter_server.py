"""Prove five-hunter staging rejects unpinned or symlinked originals."""
from pathlib import Path
import tempfile
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_five_hunter_server as stage

class FiveHunterServerSourceTests(unittest.TestCase):
    def test_source_pins_and_empty_git_blob(self):
        self.assertEqual(set(stage.PINNED), set(stage.FILES))
        self.assertEqual(len(stage.PINNED), 3)
        self.assertTrue(all(len(sha) == 40 for sha in stage.PINNED.values()))
        self.assertEqual(stage.blob_sha(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

    def test_refuse_untrusted_input_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in stage.FILES:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("not original")
            with self.assertRaisesRegex(ValueError, "Unpinned"):
                stage.stage(root)
            self.assertTrue(all((root / p).read_text() == "not original"
                                for p in stage.FILES))

    def test_refuse_symlinked_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in stage.FILES:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("not original")
            first = root / stage.FILES[0]
            first.unlink()
            first.symlink_to(root / stage.FILES[1])
            with self.assertRaisesRegex(ValueError, "Missing or linked"):
                stage.stage(root)

if __name__ == "__main__":
    unittest.main()
