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


CREDITS = (b"SEAMLESS HUNT INTERNAL NOT a public player release\\n"
           b"Yharnam Together deadinside28 Supermedo shadPS4 Wozzardman "
           b"0xCydral GPL-2.0-or-later")


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "windows.zip"

    def write(self, extra=(), *, missing=(), extra_info=()):
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name in sorted(m.REQUIRED - set(missing)):
                if name == "tools/party_boss_events.py":
                    data = b"HOST_DOOR_EFFECT = {'m29.emevd.dcx': 9920, 'm35_00_00_00.emevd.dcx': 9920}; def patch_host_door_effect(): pass"
                elif name == "CREDITS.txt":
                    data = CREDITS
                elif name == "tools/SeamlessHunt-network-profile.example.json":
                    data = b'{"schema":1,"opt_in":true,"server_ipv4":"198.51.100.24","udp_game_port":32314,"webapi_tcp_port":32315,"backend_tcp_port":21443}'
                else:
                    data = (b"Exe data " * 200) if name.endswith(".exe") else (b"sample license document and notices " * 3)
                z.writestr(m.ROOT + name, data)
            for name in extra:
                # zipfile.ZipInfo converts backslashes to slashes on Windows
                # when constructed from a plain string. Bypass that conversion
                # to simulate a malicious archive produced by a different OS.
                entry = zipfile.ZipInfo(name)
                entry.filename = name
                z.writestr(entry, "some file")
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

    def test_credits_and_redistributable_licenses_are_required(self):
        for name in ("CREDITS.txt", "LICENSE",
                     "licenses/FireBurn-FSR-Vulkan-LICENSE.txt",
                     "licenses/AMD-FidelityFX-SDK-LICENSE.txt",
                     "licenses/Intel-XeSS-LICENSE.txt",
                     "licenses/PkgTool-LICENSE.txt"):
            with self.subTest(name=name):
                self.write(missing=(name,))
                with self.assertRaisesRegex(m.UnsafeBundle, "missing required"):
                    m.check(self.archive)
        self.write()
        with zipfile.ZipFile(self.archive, "a") as z:
            z.writestr(m.ROOT + "CREDITS.txt", b"fake notices")
        with self.assertRaises(m.UnsafeBundle):
            m.check(self.archive)

    def test_guest_door_patcher_is_a_hard_release_requirement(self):
        self.write(missing=("tools/party_boss_events.py",))
        with self.assertRaisesRegex(m.UnsafeBundle, "missing required"):
            m.check(self.archive)
        with zipfile.ZipFile(self.archive, "w") as z:
            for name in sorted(m.REQUIRED):
                data = (b"fake event script" if name == "tools/party_boss_events.py"
                        else CREDITS if name == "CREDITS.txt"
                        else b'{"schema":1,"opt_in":true,"server_ipv4":"198.51.100.24","udp_game_port":32314,"webapi_tcp_port":32315,"backend_tcp_port":21443}'
                        if name == "tools/SeamlessHunt-network-profile.example.json"
                        else b"Exe data " * 200)
                z.writestr(m.ROOT + name, data)
        with self.assertRaisesRegex(m.UnsafeBundle, "co-op door event patch missing"):
            m.check(self.archive)

    def test_windows_case_collisions_and_ambiguous_profile_version_fail_closed(self):
        self.write(extra=(m.ROOT + "blauncher.exe",))
        with self.assertRaisesRegex(m.UnsafeBundle, "case-insensitive"):
            m.check(self.archive)
        self.write(extra=(m.ROOT + "TOOLS/party_boss_events.py",))
        with self.assertRaisesRegex(m.UnsafeBundle, "case-insensitive"):
            m.check(self.archive)
        self.write()
        with zipfile.ZipFile(self.archive) as z:
            files = {i.filename: z.read(i) for i in z.infolist()}
        profile = m.ROOT + "tools/SeamlessHunt-network-profile.example.json"
        for payload in (
            b'{"schema":true,"opt_in":true,"server_ipv4":"198.51.100.24","udp_game_port":32314,"webapi_tcp_port":32315,"backend_tcp_port":21443}',
            b'{"schema":1.0,"opt_in":true,"server_ipv4":"198.51.100.24","udp_game_port":32314,"webapi_tcp_port":32315,"backend_tcp_port":21443}',
        ):
            with self.subTest(payload=payload):
                with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
                    for name, data in files.items():
                        z.writestr(name, payload if name == profile else data)
                with self.assertRaisesRegex(m.UnsafeBundle, "schema-pinned"):
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
