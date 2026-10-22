"""Offline contract for explicit native legacy BBSC launch mode, not a live online test."""
from pathlib import Path
import tempfile
import unittest

import paths  # noqa: F401
import legacy_bbsc_launch as bbsc


class NativeLegacyLaunchTests(unittest.TestCase):
    def test_opt_in_is_explicit_never_implicit(self):
        environment = {"BB_PARTY": "host", "BB_BBSC": "1",
                       "BB_LEGACY_NET": "1", "BB_ONLINE": "1",
                       "BB_NET_BACKEND": "thd", "BBSC_SAVE_DIR": "/wrong/save",
                       "SHADPS4_BLOODBORNE_SEAMLESS_COOP": "1",
                       "OTHER_SETTING": "keep"}
        bbsc.clear_legacy_env(environment)
        self.assertEqual(environment["BB_PARTY"], "host")
        self.assertEqual(environment["OTHER_SETTING"], "keep")
        self.assertNotIn("BBSC_SAVE_DIR", environment)
        for key in bbsc.LEGACY_KEYS:
            self.assertNotIn(key, environment)

        bbsc.activate(environment)
        self.assertEqual(environment["BB_PARTY"], "")
        self.assertEqual(environment["BB_BBSC"], "1")
        self.assertEqual(environment["BB_LEGACY_NET"], "1")
        self.assertEqual(environment["BB_ONLINE"], "1")
        self.assertEqual(environment["BB_NET_BACKEND"], "shadnet")
        self.assertEqual(environment["SHADPS4_BLOODBORNE_SEAMLESS_COOP"], "1")
        self.assertEqual(environment["BB_SKIP_NETWORK_CHOICE"], "online")
        self.assertNotIn("BBSC_SAVE_DIR", environment)

    def test_only_explicit_candidate_allows_experimental_start(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertIn("missing", bbsc.preflight(root, party_mode="").lower())
            (root / "out" / "gpu").mkdir(parents=True)
            engine = root / "out" / "bbport.exe"
            dll = root / "out" / "gpu" / "bbnet20.dll"
            engine.write_bytes(b"MZ" + b"\x00" * 4096)
            self.assertIn("not installed", bbsc.preflight(root, party_mode=""))
            dll.write_bytes(b"MZ" + b"\x00" * 4096)
            self.assertIsNone(bbsc.preflight(root, party_mode=""))
            self.assertIn("different online protocols", bbsc.preflight(root, party_mode="host"))
            self.assertIn("different online protocols", bbsc.preflight(root, party_mode="join"))
            self.assertIn("world-warper", bbsc.preflight(root, party_mode="", warper=True))
            dll.unlink()
            self.assertIn("not installed", bbsc.preflight(root, party_mode=""))

    def test_symlinked_module_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "out" / "gpu").mkdir(parents=True)
            (root / "out" / "bbport.exe").write_bytes(b"MZ" + b"0" * 4096)
            target = root / "remote-network-module.dll"
            target.write_bytes(b"MZ" + b"0" * 4096)
            try:
                (root / "out" / "gpu" / "bbnet20.dll").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("OS does not permit test symlinks")
            self.assertIn("not installed", bbsc.preflight(root, party_mode=""))


if __name__ == "__main__":
    unittest.main()
