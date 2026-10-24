"""bbnet20 vendoring safety tests; only ephemeral local Git repos are touched."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.interop.stage_bbnet20 import REQUIRED, stage


def git(*args):
    return subprocess.check_output(["git", *map(str, args)], stderr=subprocess.DEVNULL, text=True).strip()


class StageTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.base = Path(t.name)
        self.src = self.base / "upstream"
        self.src.mkdir()
        git("-C", self.src, "init", "-q")
        git("-C", self.src, "config", "user.email", "ci@example.org")
        git("-C", self.src, "config", "user.name", "CI")
        for rel in REQUIRED:
            path = self.src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rel, encoding="utf-8")
        extra = self.src / "gpu/bbnet20/vendor/shadps4/core/net/transport.cpp"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("source", encoding="utf-8")
        git("-C", self.src, "add", ".")
        git("-C", self.src, "commit", "-q", "-m", "snapshot")
        self.sha = git("-C", self.src, "rev-parse", "HEAD")
        self.dest = self.base / "destination"

    def test_revision_manifest_and_no_overwrite(self):
        result = stage(self.src, self.dest, require_commit=self.sha)
        self.assertGreater(result["files"], len(REQUIRED))
        meta = json.loads((self.dest / "PORT-SOURCE-MANIFEST.json").read_text())
        self.assertEqual(meta["revision"], self.sha)
        self.assertTrue((self.dest / "gpu/bbnet20/vendor/shadps4/core/net/transport.cpp").is_file())
        with self.assertRaisesRegex(ValueError, "already exists"):
            stage(self.src, self.dest, require_commit=self.sha)

    def test_wrong_revision(self):
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            stage(self.src, self.dest)
        self.assertFalse(self.dest.exists())

    def test_modified_tracked_file(self):
        (self.src / "LICENSE").write_text("changed")
        with self.assertRaisesRegex(ValueError, "local edits"):
            stage(self.src, self.dest, require_commit=self.sha)

    def test_refuse_symlink(self):
        link = self.src / "gpu/bbnet20/untrusted"
        try:
            link.symlink_to(self.src / "LICENSE")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(ValueError, "symlink"):
            stage(self.src, self.dest, require_commit=self.sha)

    def test_required_missing(self):
        (self.src / "src/runtime_net.c").unlink()
        git("-C", self.src, "add", "-A")
        git("-C", self.src, "commit", "-q", "-m", "missing")
        sha = git("-C", self.src, "rev-parse", "HEAD")
        with self.assertRaisesRegex(ValueError, "required upstream"):
            stage(self.src, self.dest, require_commit=sha)


if __name__ == "__main__":
    unittest.main()
