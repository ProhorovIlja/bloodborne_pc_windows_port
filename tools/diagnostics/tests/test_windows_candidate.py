"""Offline Windows launcher archive safety and compatibility gate checks."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "check_windows_candidate.py"
spec = importlib.util.spec_from_file_location("sh_windows_bundle_gate", SCRIPT)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "windows.zip"

    def write(self, extra=(), *, missing=(), extra_info=()):
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name in sorted(m.REQUIRED - set(missing)):
                data = (b"Exe data " * 200) if name.endswith(".exe") else b"sample document"
                z.writestr(m.ROOT + name, data)
            for name in extra:
                z.writestr(name, "some file")
            for info in extra_info:
                z.writestr(info, b"unsafe link")

    def test_minimal_candidate_passes(self):
        self.write()
        result = m.check(self.archive)
        self.assertFalse(result["release_ready"])
        self.assertEqual(result["entries"], len(m.REQUIRED))
        digest = self.archive.with_suffix(".sha256")
        digest.write_text(result["sha256"] + "  " + self.archive.name + "\n", encoding="ascii")
        self.assertEqual(m.check(self.archive, sha_path=digest)["sha256"], result["sha256"])

    def test_missing_launcher_and_game_binary_fail_closed(self):
        for name in ("BLauncher.exe", "Bloodborne.exe", "bin/bb-probe.exe"):
            with self.subTest(name=name):
                self.write(missing=(name,))
                with self.assertRaisesRegex(m.UnsafeBundle, "missing required"):
                    m.check(self.archive)

    def test_game_data_and_private_credentials_rejected(self):
        for leaf in ("eboot.bin", "user/coop.json", ".env", "save.sav", "game/dvdroot_ps4/x.dat",
                     "shadnet.db", "secrets/token.txt", "foo.pfx", "game.pkg"):
            with self.subTest(leaf=leaf):
                self.write(extra=(m.ROOT + leaf,))
                with self.assertRaises(m.UnsafeBundle):
                    m.check(self.archive)

    def test_escape_and_zip_symlink_rejected(self):
        for path in ("../escape", m.ROOT + "../escape",
                     "/absolute/file", m.ROOT + "C:/bad",
                     m.ROOT + "folder\\backslash.txt"):
            with self.subTest(path=path):
                self.write(extra=(path,))
                with self.assertRaises(m.UnsafeBundle):
                    m.check(self.archive)
        link = zipfile.ZipInfo(m.ROOT + "some-link")
        link.create_system = 3
        link.external_attr = (0o120777 << 16)
        self.write(extra_info=(link,))
        with self.assertRaisesRegex(m.UnsafeBundle, "symlinks"):
            m.check(self.archive)

    def test_duplicate_member_rejected(self):
        self.write(extra=(m.ROOT + "README.md",))
        with self.assertRaisesRegex(m.UnsafeBundle, "duplicate"):
            m.check(self.archive)

    def test_checksum_corruption_rejected(self):
        self.write()
        other = self.archive.with_suffix(".sha256")
        other.write_text("0" * 64 + "  " + self.archive.name + "\n", encoding="ascii")
        with self.assertRaisesRegex(m.UnsafeBundle, "checksum"):
            m.check(self.archive, sha_path=other)
        with self.archive.open("ab") as f:
            f.write(b"trailing data")
        # Deliberate checksum is invalidated even if ZIP reader accepts trailing bytes.
        with self.assertRaisesRegex(m.UnsafeBundle, "checksum"):
            m.check(self.archive, sha_path=other)


if __name__ == "__main__":
    unittest.main()
