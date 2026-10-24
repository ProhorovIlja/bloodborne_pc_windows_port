"""Offline coupled native Bloodborne Windows candidate safety tests, no game assets."""
import importlib.util
from pathlib import Path
import json
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).with_name("assemble_windows_test_kit.py")
spec = importlib.util.spec_from_file_location("shyt_v41_assembly", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

TOOLS = {
    "BLauncher.exe", "Bloodborne.exe", "bin/bb-probe.exe", "bin/bb-gpu-capabilities.exe",
    "run.py", "README.md", "LICENSE", "tools/party_boss_events.py",
    "tools/SeamlessHunt-network-profile.example.json",
    "CREDITS.txt", "licenses/FireBurn-FSR-Vulkan-LICENSE.txt",
    "licenses/AMD-FidelityFX-SDK-LICENSE.txt", "licenses/Intel-XeSS-LICENSE.txt",
    "licenses/PkgTool-LICENSE.txt",
}
EVENT = b"HOST_DOOR_EFFECT = {'m29.emevd.dcx': 9920, 'm35_00_00_00.emevd.dcx': 9920}\ndef patch_host_door_effect(x): return x\n"


class CoupledKitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.game = base / "native_game.zip"
        self.server = base / "native_server.zip"
        self.out = base / "combined.zip"
        self.make_game()
        self.make_server()

    def make_game(self, added=None):
        with zipfile.ZipFile(self.game, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name in sorted(TOOLS):
                if name.endswith("party_boss_events.py"):
                    data = EVENT
                elif name == "CREDITS.txt":
                    data = (b"SEAMLESS HUNT NOT a public release Yharnam Together "
                            b"deadinside28 Supermedo shadPS4 Wozzardman 0xCydral "
                            b"GPL-2.0-or-later")
                else:
                    data = (b"Executable" * 200 if name.endswith(".exe")
                            else b"Original open-source library licensing notices " * 3)
                z.writestr("bbport-windows/" + name, data)
            if added:
                z.writestr("bbport-windows/" + added, b"test")

    def make_server(self, missing=None, added=None):
        with zipfile.ZipFile(self.server, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name in sorted(mod.SERVER_FILES - ({missing} if missing else set())):
                if name == "server/CREDITS.txt":
                    data = (b"Yharnam Together deadinside28 Supermedo "
                            b"original contributor author copyright and license " * 8)
                elif name == "server/licenses/Qt-6.8.3-LICENSE-SCOPE.txt":
                    data = (b"Qt HTTP Server GPL v3; not LGPL v3; "
                            b"source, redistribution, corresponding license review " * 8)
                elif name.endswith(".txt"):
                    data = b"Original license rights and conditions reproduced for testing " * 8
                else:
                    data = b"Native qt or shadnet" * 110 if name.endswith((".dll", ".exe")) else b"test config"
                z.writestr(name, data)
            if added:
                z.writestr(added, b"test")

    def test_complete_client_plus_server_staged_but_not_approved(self):
        result = mod.assemble(self.game, self.server, self.out)
        self.assertFalse(result["release_ready"])
        with zipfile.ZipFile(self.out) as z:
            files = set(z.namelist())
            for name in mod.SERVER_FILES:
                self.assertIn("bbport-windows/" + name, files)
            self.assertIn("bbport-windows/BLauncher.exe", files)
            meta = json.loads(z.read("bbport-windows/SHYT-INTERNAL-CANDIDATE-MANIFEST.json"))
            self.assertFalse(meta["release_ready"])
            self.assertEqual(meta["game_zip_sha256"], mod.digest(self.game))
            self.assertIn(b"INTERNAL", z.read("bbport-windows/NOT-FOR-PUBLIC-RELEASE.txt"))
            self.assertNotIn("bbport-windows/eboot.bin", files)

    def test_missing_native_server_library_cannot_be_distributed(self):
        for missing in ("server/shadnet.exe", "server/Qt6Core.dll",
                        "server/Qt6Concurrent.dll", "server/Qt6HttpServer.dll",
                        "server/sqldrivers/qsqlite.dll", "backend/bb_dummy_server.py",
                        "server/CREDITS.txt", "server/licenses/GPL-3.0.txt",
                        "server/licenses/LGPL-3.0.txt",
                        "server/licenses/Qt-6.8.3-LICENSE-SCOPE.txt"):
            with self.subTest(missing=missing):
                self.make_server(missing=missing)
                with self.assertRaisesRegex(mod.InvalidCandidate, "missing"):
                    mod.assemble(self.game, self.server, self.out)

    def test_windows_archive_containing_saves_or_keys_is_rejected(self):
        for name in ("server/shadnet.db", "backend/.env",
                     "game/dvdroot_ps4/common.emevd.dcx", "user/coop.json",
                     "server/key.pem"):
            with self.subTest(name=name):
                self.make_server(added=name)
                with self.assertRaises(mod.InvalidCandidate):
                    mod.assemble(self.game, self.server, self.out)

    def test_bad_server_checksum_and_missing_event_script(self):
        chk = self.server.with_suffix(".sha256")
        chk.write_text("0" * 64 + "  " + self.server.name + "\n", encoding="ascii")
        with self.assertRaisesRegex(mod.InvalidCandidate, "SHA256"):
            mod.assemble(self.game, self.server, self.out, server_sha=chk)
        with zipfile.ZipFile(self.game, "w") as z:
            for name in sorted(TOOLS - {"tools/party_boss_events.py"}):
                z.writestr("bbport-windows/" + name, b"Executable" * 200)
        with self.assertRaises(ValueError):
            mod.assemble(self.game, self.server, self.out)

    def test_zip_escape_and_duplicate_contents_blocked(self):
        self.make_server(added="../escape.txt")
        with self.assertRaises(mod.InvalidCandidate):
            mod.assemble(self.game, self.server, self.out)
        with zipfile.ZipFile(self.server, "a") as z:
            z.writestr("server/shadnet.exe", b"spoofed")
        with self.assertRaises(mod.InvalidCandidate):
            mod.assemble(self.game, self.server, self.out)

    def test_output_cannot_replace_input_archives(self):
        with self.assertRaisesRegex(mod.InvalidCandidate, "overwrite"):
            mod.assemble(self.game, self.server, self.game)


if __name__ == "__main__":
    unittest.main()
