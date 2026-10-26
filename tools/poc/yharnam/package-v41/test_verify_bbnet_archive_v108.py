"""V108 real bbnet member-name and V101 source provenance regression."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).with_name("verify_bbnet_archive_v108.py")
SPEC = importlib.util.spec_from_file_location("v108_archive_guard", FILE)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
ROOT_NAMES = (
    "bloodborne_flags.h", "bloodborne_flags_store.cpp",
    "bloodborne_party.h", "bloodborne_party.cpp",
    "bloodborne_party_death.cpp", "bloodborne_re_internal.h",
    "bloodborne_re.cpp",
)
AR_LIST = "\\n".join(name + ".obj" for name in guard.REQUIRED_UNITS) + "\\n"


class TestV108NativeArchive(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "libbbnet.a"
        self.archive.write_bytes(b"!<arch>\\nnonempty-fixture")
        self.manifest = self.root / "shyt-v101-gameplay-source.json"
        digests = {}
        for name in ROOT_NAMES:
            relative = "emulator/src/core/" + name
            file = self.root / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            data = ("source fixture: " + name).encode("utf-8")
            file.write_bytes(data)
            digests[relative] = hashlib.sha256(data).hexdigest()
        self.report = {
            "pinned_upstream": guard.PIN,
            "development_only": True,
            "native_gameplay_direct_udp_enabled": False,
            "native_game_translation_units_verified": True,
            "source_sha256": digests,
        }
        self.write_report()

    def write_report(self):
        self.manifest.write_text(json.dumps(self.report), encoding="utf-8")

    def test_pass_with_four_exact_native_game_objects(self):
        with patch.object(guard.subprocess, "check_output", return_value=AR_LIST) as run:
            guard.verify(self.archive, self.manifest, self.root)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][:2], ["llvm-ar", "t"])

    def test_fail_on_missing_or_duplicate_object(self):
        samples = (
            AR_LIST.replace("bloodborne_party_death.cpp.obj\\n", ""),
            AR_LIST + "bloodborne_party.cpp.obj\\n",
            "unrelated.cpp.obj\\n",
        )
        for listing in samples:
            with self.subTest(listing=listing), patch.object(
                guard.subprocess, "check_output", return_value=listing
            ), self.assertRaisesRegex(ValueError, "game C\\+\\+ object"):
                guard.verify(self.archive, self.manifest, self.root)

    def test_fail_on_changed_original_game_source(self):
        (self.root / "emulator/src/core/bloodborne_party.cpp").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "changed after V101 stage"):
            guard.verify(self.archive, self.manifest, self.root)

    def test_fail_on_unsafe_manifest_and_unexpected_digest(self):
        for key, value in (
            ("pinned_upstream", "different-source-pin"),
            ("native_gameplay_direct_udp_enabled", True),
            ("development_only", False),
            ("native_game_translation_units_verified", False),
        ):
            saved = self.report[key]
            self.report[key] = value
            self.write_report()
            with self.subTest(field=key), self.assertRaises(ValueError):
                guard.verify_manifest(self.manifest, self.root)
            self.report[key] = saved
        k = "emulator/src/core/bloodborne_re.cpp"
        self.report["source_sha256"][k] = "0" * 64
        self.write_report()
        with self.assertRaisesRegex(ValueError, "changed after V101 stage"):
            guard.verify_manifest(self.manifest, self.root)

    def test_empty_archive_cannot_count_as_real_game(self):
        self.archive.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "missing or empty"):
            guard.verify_archive(self.archive)


if __name__ == "__main__":
    unittest.main()
