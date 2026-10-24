"""Offline capacity model checks; all rates are assumptions, not measurements."""
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "game_traffic_capacity.py"
spec = importlib.util.spec_from_file_location("shyt_capacity", SCRIPT)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class TrafficCapacityTests(unittest.TestCase):
    def test_current_server_relay_all_payloads_once_in_then_fanout(self):
        result = model.estimate(hunters=3, parties=2, hunter_payload_kbps=64)
        self.assertEqual(result["server_relay_game_ingress_mbps"], 0.384)
        self.assertEqual(result["server_relay_game_egress_mbps"], 0.768)
        self.assertEqual(result["clients_total_direct_game_egress_mbps"], 0)
        self.assertEqual(result["current_upstream_mode"], "server_relay_udp")
        self.assertFalse(result["release_ready"])
        self.assertFalse(result["server_cpu_ram_rtt_loss_measured"])

    def test_hypothetical_half_direct_saves_only_some_relay_not_world_state(self):
        result = model.estimate(
            hunters=5, parties=100, hunter_payload_kbps=80,
            direct_fraction=0.5, overhead_fraction=0.1)
        self.assertEqual(result["server_relay_game_ingress_mbps"], 22)
        self.assertEqual(result["server_relay_game_egress_mbps"], 88)
        self.assertEqual(result["clients_total_direct_game_egress_mbps"], 88)
        self.assertFalse(result["world_state_control_bytes_included"])
        self.assertIn("HYPOTHETICAL", result["transport"])

    def test_invalid_or_unbounded_inputs_rejected(self):
        cases = (
            {"hunters": 1, "parties": 3, "hunter_payload_kbps": 50},
            {"hunters": 2, "parties": 0, "hunter_payload_kbps": 50},
            {"hunters": 2, "parties": 3, "hunter_payload_kbps": float("nan")},
            {"hunters": 2, "parties": 3, "hunter_payload_kbps": -5},
            {"hunters": 3, "parties": 5, "hunter_payload_kbps": 45, "direct_fraction": 1.5},
            {"hunters": 3, "parties": 5, "hunter_payload_kbps": 45, "overhead_fraction": -0.1},
        )
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                model.estimate(**args)

    def test_cli_rejects_p2p_claim_without_explicit_model_acknowledgement(self):
        command = [sys.executable, str(SCRIPT), "--hunters", "4", "--parties", "7",
                   "--per-hunter-kbps", "50", "--experimental-direct-pct", "50"]
        denied = subprocess.run(command, text=True, capture_output=True)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("P2P is not in the current", denied.stderr)
        allowed = subprocess.run(command + ["--allow-hypothetical-p2p"],
                                 text=True, capture_output=True)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        result = json.loads(allowed.stdout)
        self.assertFalse(result["direct_p2p_in_pinned_game_verified"])
        self.assertFalse(result["release_ready"])


if __name__ == "__main__":
    unittest.main()
