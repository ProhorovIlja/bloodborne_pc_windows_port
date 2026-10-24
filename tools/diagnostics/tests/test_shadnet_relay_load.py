"""Real shadNet tick-line traffic analyzer, no PII in outputs."""
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "shadnet_relay_load.py"
spec = importlib.util.spec_from_file_location("shyt_relay_counter_v44", SCRIPT)
load = importlib.util.module_from_spec(spec)
# dataclasses resolves __module__ through sys.modules during class creation.
sys.modules[spec.name] = load
spec.loader.exec_module(load)


class RelayLoadTests(unittest.TestCase):
    def test_multiple_members_and_windows_are_summed_without_identities(self):
        lines = [
            '2026-10-24T20:01:10Z server link: "Alice 198.51.100.1:35201" in 300 frames/30000 bytes, out 450 frames/50000 bytes, 10 pings',
            '2026-10-24T20:01:10Z server link: Bob 203.0.113.42:20000 in 200 frames/20000 bytes, out 100 frames/17000 bytes, 10 pings',
            '2026-10-24T20:01:20Z server link: Alice 198.51.100.1:35201 in 100 frames/8000 bytes, out 130 frames/9000 bytes, 10 pings',
            'another line unrelated to relay stats',
        ]
        result = load.parse(lines).summary(duration_seconds=20)
        self.assertEqual(result["sampled_link_windows"], 3)
        self.assertEqual(result["relay_game_payload_bytes_in"], 58000)
        self.assertEqual(result["relay_game_payload_bytes_out"], 76000)
        self.assertEqual(result["relay_game_frames_in"], 600)
        self.assertEqual(result["relay_payload_egress_mbps_approx"], 0.0304)
        self.assertNotIn("Alice", str(result))
        self.assertNotIn("198.51.100.1", str(result))
        self.assertFalse(result["lobby_and_world_control_bytes_included"])
        self.assertFalse(result["cpu_ram_and_direct_p2p_measured"])

    def test_no_samples_is_not_claimed_zero_load(self):
        result = load.parse(["server started", "no game clients currently"]).summary()
        self.assertEqual(result["sampled_link_windows"], 0)
        self.assertNotIn("relay_payload_egress_mbps_approx", result)

    def test_malformed_or_64_bit_overflow_cannot_be_used_as_measurement(self):
        too_wide = "server link: Person in 0 frames/18446744073709551616 bytes, out 0 frames/0 bytes, 0 pings"
        with self.assertRaisesRegex(ValueError, "wider-than-64-bit"):
            load.parse([too_wide])
        count = load.parse(["server link: A in 1 frames/42 bytes, out 2 frames/59 bytes, 0 pings"])
        for duration in (0, -10, 32_000_000):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                count.summary(duration_seconds=duration)
        with self.assertRaisesRegex(ValueError, "bounded"):
            load.parse(["nope"] * 11, max_lines=10)


if __name__ == "__main__":
    unittest.main()
