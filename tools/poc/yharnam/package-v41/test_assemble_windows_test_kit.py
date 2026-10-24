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
    "CREDITS.txt", "SHYT-SOURCE-IDENTITY.json", "licenses/FireBurn-FSR-Vulkan-LICENSE.txt",
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
                elif name == "tools/SeamlessHunt-network-profile.example.json":
                    data = b'{"schema":1,"opt_in":true,"server_ipv4":"198.51.100.24","udp_game_port":32314,"webapi_tcp_port":32315,"backend_tcp_port":21443}'
                elif name == "SHYT-SOURCE-IDENTITY.json":
                    data = (json.dumps({
                        "schema": 1, "component": "game",
                        "source_commit": "1" * 40,
                        "upstream_pin": "77e350743a7cb4524cfcc1782fb6e3af64e25b15",
                        "release_ready": False}) + "\n").encode("utf-8")
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
                if name == "SHYT-SOURCE-IDENTITY.json":
                    data = (json.dumps({"schema": 1, "component": "server",
                                        "source_commit": "1" * 40,
                                        "upstream_pin": "77e350743a7cb4524cfcc1782fb6e3af64e25b15",
                                        "release_ready": False}) + "\n").encode("utf-8")
                elif name == "server/CREDITS.txt":
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
            self.assertEqual(meta["seamless_hunt_source_commit"], "1" * 40)
            self.assertIn(b"INTERNAL", z.read("bbport-windows/NOT-FOR-PUBLIC-RELEASE.txt"))
            self.assertNotIn("bbport-windows/eboot.bin", files)

    def test_missing_native_server_library_cannot_be_distributed(self):
        for missing in ("server/shadnet.exe", "server/Qt6Core.dll",
                        "server/Qt6Network.dll", "server/Qt6Sql.dll",
                        "server/Qt6HttpServer.dll",
                        "server/sqldrivers/qsqlite.dll", "backend/bb_dummy_server.py",
                        "server/CREDITS.txt", "server/licenses/GPL-3.0.txt",
                        "server/licenses/LGPL-3.0.txt",
                        "server/licenses/Qt-6.8.3-LICENSE-SCOPE.txt"):
            with self.subTest(missing=missing):
                self.make_server(missing=missing)
                with self.assertRaisesRegex(mod.InvalidCandidate, "missing"):
                    mod.assemble(self.game, self.server, self.out)

    def test_rejects_server_from_a_different_seamless_hunt_commit(self):
        with zipfile.ZipFile(self.server) as z:
            entries = {x.filename: z.read(x) for x in z.infolist()}
        mismatched = json.loads(entries["SHYT-SOURCE-IDENTITY.json"])
        mismatched["source_commit"] = "2" * 40
        entries["SHYT-SOURCE-IDENTITY.json"] = json.dumps(mismatched).encode("utf-8")
        with zipfile.ZipFile(self.server, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in entries.items():
                z.writestr(name, data)
        with self.assertRaisesRegex(mod.InvalidCandidate, "source commit mismatch"):
            mod.assemble(self.game, self.server, self.out)

    def test_rejects_missing_or_forged_source_identity(self):
        for component in ("game", "server"):
            archive = self.game if component == "game" else self.server
            self.make_game()
            self.make_server()
            with zipfile.ZipFile(archive) as z:
                entries = {x.filename: z.read(x) for x in z.infolist()}
            member = ("bbport-windows/" if component == "game" else "") + "SHYT-SOURCE-IDENTITY.json"
            for variant in ("missing", "schema_boolean", "wrong_pin"):
                modified = dict(entries)
                if variant == "missing":
                    modified.pop(member)
                else:
                    identity = json.loads(modified[member])
                    if variant == "schema_boolean":
                        identity["schema"] = True
                    else:
                        identity["upstream_pin"] = "0" * 40
                    modified[member] = json.dumps(identity).encode("utf-8")
                with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
                    for name, data in modified.items():
                        z.writestr(name, data)
                with self.subTest(component=component, variant=variant):
                    with self.assertRaisesRegex((mod.InvalidCandidate, ValueError), "source identity"):
                        mod.assemble(self.game, self.server, self.out)
            self.make_game()
            self.make_server()

    def test_qt_concurrent_is_optional_in_real_native_server(self):
        self.assertNotIn("server/Qt6Concurrent.dll", mod.SERVER_FILES)
        result = mod.assemble(self.game, self.server, self.out)
        self.assertFalse(result["release_ready"])
        with zipfile.ZipFile(self.out) as z:
            self.assertNotIn("bbport-windows/server/Qt6Concurrent.dll", z.namelist())
            for dll in ("Qt6Core.dll", "Qt6Network.dll", "Qt6Sql.dll", "Qt6HttpServer.dll"):
                self.assertIn("bbport-windows/server/" + dll, z.namelist())

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

    def test_case_insensitive_windows_collision_across_both_bundles(self):
        self.make_server(added="server/SHADNET.exe")
        with self.assertRaisesRegex(mod.InvalidCandidate, "case-insensitive"):
            mod.assemble(self.game, self.server, self.out)
        self.make_server()
        self.make_game(added="server/qt6core.dll")
        with self.assertRaisesRegex(mod.InvalidCandidate, "collision"):
            mod.assemble(self.game, self.server, self.out)

    def test_output_cannot_replace_input_archives(self):
        with self.assertRaisesRegex(mod.InvalidCandidate, "overwrite"):
            mod.assemble(self.game, self.server, self.game)


if __name__ == "__main__":
    unittest.main()
