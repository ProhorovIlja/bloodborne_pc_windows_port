"""Ensure packaged Ubuntu/Windows Qt servers match the advertised source hash."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("shyt_server_v45_stage_test", HERE / "stage_hotpath.py")
stager = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = stager
spec.loader.exec_module(stager)
from test_patch_server_hotpath import RELAY_OLD


class PinAndIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.overlay = Path(self.tmp.name) / "composed"
        self.source = self.overlay / stager.SOURCE
        self.source.parent.mkdir(parents=True)
        self.source.write_text(RELAY_OLD, encoding="utf-8")
        self.original_digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.manifest = self.overlay / stager.MANIFEST
        self.payload = {
            "upstream_pin": stager.PIN,
            "applied": ["V3 in-game UI scale", "V29 bounded RPC"],
            "sha256": {stager.SOURCE: self.original_digest},
            "public_release_ready": False,
        }
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.payload), encoding="utf-8")

    def test_actual_staging_rewrites_both_bytes_and_verified_manifest(self):
        patched_bytes, updated_json = stager.prepare(self.overlay)
        self.assertIn(b"SHYT-SERVER-RELAY-PERF-V45", patched_bytes)
        self.assertIn(stager.IDENT, json.loads(updated_json)["applied"])
        self.assertEqual(self.source.read_text(), RELAY_OLD)
        stager.stage(self.overlay)
        recorded = json.loads(self.manifest.read_text("utf-8"))
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),
                         recorded["sha256"][stager.SOURCE])
        self.assertEqual(recorded["native_udp_hotpath"]["old_sha256"],
                         self.original_digest)
        self.assertFalse(recorded["native_udp_hotpath"]["game_protocol_changed"])
        self.assertFalse(recorded["native_udp_hotpath"]["real_cpu_or_relay_bandwidth_improvement_verified"])
        self.assertFalse(recorded["public_release_ready"])
        self.assertEqual(recorded["applied"].count(stager.IDENT), 1)
        self.assertFalse(list(self.overlay.rglob("*.pending-v45")))

    def test_second_staging_must_fail_without_file_mutation(self):
        stager.stage(self.overlay)
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "already staged"):
            stager.stage(self.overlay)
        self.assertEqual(self.source.read_bytes(), before)

    def test_tampering_with_source_or_digest_does_not_mutate_manifest(self):
        self.source.write_bytes(self.source.read_bytes() + b"\n// injection")
        before = self.manifest.read_bytes()
        with self.assertRaisesRegex(ValueError, "does not match"):
            stager.stage(self.overlay)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_wrong_pin_or_release_flag_is_rejected(self):
        for field, value in (
            ("upstream_pin", "other-build"),
            ("public_release_ready", True),
        ):
            with self.subTest(field=field):
                self.payload[field] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "pin or unsafe release"):
                    stager.stage(self.overlay)
                self.payload[field] = False if field == "public_release_ready" else stager.PIN
                self.save()

    def test_source_drift_fails_without_emitting_false_hash(self):
        self.source.write_bytes(b"// SPDX-License-Identifier: GPL-2.0-or-later\nwrong")
        self.payload["sha256"][stager.SOURCE] = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.save()
        manifest = self.manifest.read_bytes()
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            stager.stage(self.overlay)
        self.assertEqual(self.manifest.read_bytes(), manifest)


if __name__ == "__main__":
    unittest.main()
