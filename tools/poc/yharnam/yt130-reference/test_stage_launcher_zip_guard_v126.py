"""Windows self-update ZIP safety regressions, no network/real game required."""
from __future__ import annotations
import importlib.util
import io
from pathlib import Path
import stat
import unittest
import zipfile

spec = importlib.util.spec_from_file_location(
    "yt130_zipguard", Path(__file__).with_name("stage_launcher_zip_guard_v126.py"))
assert spec and spec.loader
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)

namespace: dict = {}
exec(compile(stage.HELPER, "<YT130 V126 update validator>", "exec"), namespace)
validate = namespace["validate_bbport_update_zip"]
FILES = [
    "bbport-windows/BLauncher.exe",
    "bbport-windows/Bloodborne.exe",
    "bbport-windows/bin/bb-probe.exe",
    "bbport-windows/bin/bb-gpu-capabilities.exe",
]


def archive(names=FILES, link=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            if name == link:
                member = zipfile.ZipInfo(name)
                member.create_system = 3
                member.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(member, b"target")
            else:
                z.writestr(name, b"valid-" + name.encode("ascii", errors="replace"))
    out.seek(0)
    return zipfile.ZipFile(out)


class ZipUpdateGuardTests(unittest.TestCase):
    def test_realistic_official_root_and_binary_files_allowed(self):
        with archive() as z:
            self.assertTrue(validate(z))

    def test_rejects_duplicate_windows_case_variants(self):
        with archive(FILES + ["bbport-windows/blauncher.exe"]) as z:
            with self.assertRaises(ValueError):
                validate(z)

    def test_rejects_absolute_traversal_backslash_and_foreign_root(self):
        for path in ("bbport-windows/../escape.exe", "/bbport-windows/escape.exe",
                     "bbport-windows/other\\escape.exe", "other/BLauncher.exe",
                     "bbport-windows/bin/CON.exe", "bbport-windows/file.exe ",
                     "bbport-windows/bin/name:stream.exe"):
            with self.subTest(path=path):
                with archive(FILES + [path]) as z:
                    if chr(92) in path:
                        # Windows' ZipInfo normalizes backslashes while reading;
                        # inject a raw incoming entry name into the ZipInfo
                        # object to test this guard independently of zipfile's
                        # platform-specific decoding policy.
                        z.infolist()[-1].filename = path
                        self.assertEqual(z.infolist()[-1].filename, path)
                    with self.assertRaises(ValueError):
                        validate(z)

    def test_rejects_symlink_and_missing_game_exe(self):
        with archive(FILES + ["bbport-windows/bin/link"], link="bbport-windows/bin/link") as z:
            with self.assertRaises(ValueError):
                validate(z)
        with archive(FILES[:-1]) as z:
            with self.assertRaises(ValueError):
                validate(z)

    def test_rejects_declared_expansion_bomb_before_extraction(self):
        class BigFile:
            filename = "bbport-windows/BLauncher.exe"
            file_size = 4 * 1024**3
            compress_size = 5
            flag_bits = 0
            external_attr = 0
            def is_dir(self):
                return False
        class FakeZip:
            def infolist(self):
                return [BigFile()]
            def testzip(self):
                raise AssertionError("Must refuse huge expansion without decompressing")
        with self.assertRaises(ValueError):
            validate(FakeZip())

    def test_rejects_staged_source_drifts_and_repetition(self):
        original = (
            "atomic_utf8_write\nrecord_startup_failure\n"
            + stage.HELPER_ANCHOR + "\n"
            + stage.DOWNLOAD_ANCHOR + "\n"
            + stage.CHUNK_ANCHOR + "\n"
            + stage.EXTRACT_ANCHOR + "\n"
            + stage.FIND_ANCHOR + "\n"
            + stage.EXCEPTION_ANCHOR + "\n"
        )
        rewritten = stage.rewrite(original)
        self.assertIn("validate_bbport_update_zip(package)", rewritten)
        self.assertIn("done > MAX_BBPORT_UPDATE_DOWNLOAD", rewritten)
        self.assertIn("package.extractall", rewritten)
        with self.assertRaises(ValueError):
            stage.rewrite(rewritten)
        with self.assertRaises(ValueError):
            stage.rewrite(original.replace(stage.EXTRACT_ANCHOR, "unsafe_extract()"))


if __name__ == "__main__":
    unittest.main()
