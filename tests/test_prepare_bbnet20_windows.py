"""Offline Win64 bbnet20 source-port regression tests; synthetic sources only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.interop.prepare_bbnet20_windows import CMAKE, EXPORT, FORMAT, GLUE, LINK_OPTS, REVISION, prepare


class NativeBbscPrepareTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.staged = root / "staged"
        self.staged.mkdir()
        self.workspace = root / "windows"
        (self.workspace / "gpu").mkdir(parents=True)
        (self.workspace / "gpu/CMakeLists.txt").write_text("project(test)")
        files = {GLUE: EXPORT.encode(), CMAKE: LINK_OPTS.encode(),
                 "gpu/bbnet20/vendor/shadps4/network.cpp": b"vendor",
                 "gpu/bbnet/bbnet.h": b"ABI2",
                 "gpu/third_party/httplib/httplib.h": b"HTTP",
                 "gpu/third_party/httplib/LICENSE": b"MIT"}
        self.manifest = {"format": FORMAT, "revision": REVISION, "files": []}
        for name, data in files.items():
            f = self.staged / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            self.manifest["files"].append({
                "path": name, "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest()})
        self.save()

    def save(self):
        (self.staged / "PORT-SOURCE-MANIFEST.json").write_text(json.dumps(self.manifest))

    def test_stages_and_rejects_overwrite(self):
        result = prepare(self.staged, self.workspace)
        self.assertEqual(result["files_staged"], 6)
        self.assertFalse(result["windows_online_dll_built"])
        self.assertIn("__declspec(dllexport)", (self.workspace / GLUE).read_text())
        self.assertIn("if(NOT WIN32)", (self.workspace / CMAKE).read_text())
        self.assertIn("$"+"{CMAKE_SOURCE_DIR}", (self.workspace / CMAKE).read_text())
        self.assertEqual((self.workspace / "gpu/bbnet20/vendor/shadps4/network.cpp").read_bytes(), b"vendor")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            prepare(self.staged, self.workspace)

    def test_fail_closed_revision_hash_and_signatures(self):
        self.manifest["revision"] = "f" * 40
        self.save()
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            prepare(self.staged, self.workspace)
        self.manifest["revision"] = REVISION
        self.save()
        (self.staged / GLUE).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA256"):
            prepare(self.staged, self.workspace)
        blob = b"changed upstream ABI"
        (self.staged / GLUE).write_bytes(blob)
        record = next(x for x in self.manifest["files"] if x["path"] == GLUE)
        record.update(size=len(blob), sha256=hashlib.sha256(blob).hexdigest())
        self.save()
        with self.assertRaisesRegex(ValueError, "review Windows adaptations"):
            prepare(self.staged, self.workspace)

    def test_reject_source_traversal(self):
        self.manifest["files"].append({
            "path": "gpu/bbnet20/../other.cpp", "size": 0, "sha256": "0"*64})
        self.save()
        with self.assertRaisesRegex(ValueError, "unsafe"):
            prepare(self.staged, self.workspace)


if __name__ == "__main__":
    unittest.main()
