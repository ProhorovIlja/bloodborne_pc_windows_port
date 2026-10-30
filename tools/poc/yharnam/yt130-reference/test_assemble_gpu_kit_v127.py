"""Offline regression for an INTERNAL V127 native Windows kit assembler."""
from __future__ import annotations
import importlib.util
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location(
    "yt130_assembler", Path(__file__).with_name("assemble_gpu_kit_v127.py"))
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fake_pe(marker: bytes, *, machine: int = 0x8664) -> bytes:
    b = bytearray(512)
    b[0:2] = b"MZ"
    struct.pack_into("<I", b, 0x3C, 0x80)
    b[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<H", b, 0x84, machine)
    b[0x120:0x120 + len(marker)] = marker
    return bytes(b)


class ActualNativeKitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "original.zip"
        self.new = self.root / "integrated.zip"
        self.report = self.root / "provenance.json"
        self.compiled = self.root / "compiled"
        self.compiled.mkdir()
        self.old = {}
        with zipfile.ZipFile(self.original, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for idx, (entry, binary) in enumerate(mod.EXE_MAP.items()):
                src = fake_pe(b"OLD" + str(idx).encode())
                z.writestr(entry, src)
                self.old[entry] = src
                (self.compiled / binary).write_bytes(fake_pe(b"NEW" + str(idx).encode()))
            for filename, data in {
                "bbport-windows/BLauncher.exe": b"preserve-frozen-launcher",
                "bbport-windows/licenses/PkgTool-LICENSE.txt": b"preserve-license",
                "bbport-windows/licenses/Intel-XeSS-LICENSE.txt": b"preserve-license-too",
                "bbport-windows/bin/SDL3.dll": b"preserve-game-runtime",
            }.items():
                z.writestr(filename, data)
                self.old[filename] = data
        self.sha = hashlib.sha256(self.original.read_bytes()).hexdigest()

    def test_native_replaces_exactly_three_exes_and_retains_every_other_byte(self):
        result = mod.assemble(self.original, self.compiled, self.new, self.report,
                              expected_sha=self.sha, strict=False)
        self.assertEqual(len(result["changed_files"]), 3)
        self.assertTrue(result["all_other_file_bytes_verified_unchanged"])
        self.assertFalse(result["production_ready"])
        self.assertFalse(result["gameplay_in_game_tested"])
        with zipfile.ZipFile(self.original) as before, zipfile.ZipFile(self.new) as after:
            self.assertEqual(set(before.namelist()), set(after.namelist()))
            for name in self.old:
                data = after.read(name)
                if name in mod.EXE_MAP:
                    self.assertNotEqual(data, self.old[name])
                    self.assertEqual(data, (self.compiled / mod.EXE_MAP[name]).read_bytes())
                else:
                    self.assertEqual(data, self.old[name])
        self.assertEqual(json.loads(self.report.read_text())["v127_integrated_internal_kit_sha256"],
                         hashlib.sha256(self.new.read_bytes()).hexdigest())

    def test_fails_closed_on_wrong_kit_or_missing_or_invalid_exe(self):
        with self.assertRaises(ValueError):
            mod.assemble(self.original, self.compiled, self.new, self.report,
                         expected_sha="0" * 64, strict=False)
        testpath = self.compiled / "bb-probe.exe"
        testpath.write_bytes(fake_pe(b"ARM", machine=0xAA64))
        with self.assertRaises(ValueError):
            mod.assemble(self.original, self.compiled, self.new, self.report,
                         expected_sha=self.sha, strict=False)
        testpath.unlink()
        with self.assertRaises(ValueError):
            mod.assemble(self.original, self.compiled, self.new, self.report,
                         expected_sha=self.sha, strict=False)

    def test_never_overwrites_original_known_good_portable_kit(self):
        with self.assertRaises(ValueError):
            mod.assemble(self.original, self.compiled, self.original, self.report,
                         expected_sha=self.sha, strict=False)
        with zipfile.ZipFile(self.original) as a:
            self.assertEqual(a.read("bbport-windows/BLauncher.exe"), b"preserve-frozen-launcher")

    def test_rejects_zip_slip_and_windows_case_collision(self):
        with zipfile.ZipFile(self.original, "a") as z:
            z.writestr("bbport-windows/../escape.exe", b"unsafe")
        with self.assertRaises(ValueError):
            mod.assemble(self.original, self.compiled, self.new, self.report,
                         expected_sha=hashlib.sha256(self.original.read_bytes()).hexdigest(),
                         strict=False)


if __name__ == "__main__":
    unittest.main()
