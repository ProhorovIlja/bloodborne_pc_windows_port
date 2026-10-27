"""Security and source-origin tests for official YT PR429 launcher staging."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name("stage.py")
spec = importlib.util.spec_from_file_location("native_yt_truststore", path)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class LauncherTruststoreStaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patch = stage.PATCH.read_text(encoding="utf-8")

    def test_upstream_diff_only_five_pinned_paths(self):
        stage.check_patch(self.patch)
        self.assertEqual(stage.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(len(stage.BLOBS), 5)
        self.assertNotIn("server/", "\n".join(stage.BLOBS))
        self.assertEqual(set(a for a, b in stage.GIT_DIFF.findall(self.patch)),
                         set(stage.BLOBS))

    def test_missing_package_or_release_probe_is_rejected(self):
        for missing in ("--hidden-import truststore", "|True|True", "ssl.CERT_REQUIRED"):
            with self.subTest(missing=missing):
                with self.assertRaises(ValueError):
                    stage.check_patch(self.patch.replace(missing, "REMOVED"))

    def test_tls_bypass_and_unexpected_source_disallowed(self):
        for line in ("CERT_NONE", "check_hostname=False", "verify=False"):
            with self.subTest(line=line):
                with self.assertRaises(ValueError):
                    stage.check_patch(self.patch + "\n" + line)
        with self.assertRaises(ValueError):
            stage.check_patch(self.patch + "\ndiff --git a/server/secrets.cpp b/server/secrets.cpp")

    def test_no_live_data_change_or_native_network_replacement(self):
        self.assertIn("bbport/launcher/bbport_coop.py", stage.BLOBS)
        self.assertTrue(all(("bbport/" in p or p == "tools/make-release.ps1")
                            for p in stage.BLOBS))
        self.assertNotIn("ssl._create_unverified_context", self.patch)


if __name__ == "__main__":
    unittest.main()
