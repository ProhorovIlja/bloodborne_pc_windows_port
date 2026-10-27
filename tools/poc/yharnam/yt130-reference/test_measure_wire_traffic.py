"""Traffic counters are aggregate only, and never expose user private data."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("measure_wire_traffic.py")
spec = importlib.util.spec_from_file_location("measure_wire", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class WireAggregationTests(unittest.TestCase):
    def test_realistic_two_intervals(self):
        lines = [
            "INFO YT130_WIRE_TRAFFIC kind=3 in_packets=40 in_bytes=8000 out_packets=40 out_bytes=9000",
            "INFO YT130_WIRE_TRAFFIC kind=7 in_packets=200 in_bytes=25000 out_packets=900 out_bytes=65000",
            "INFO YT130_WIRE_TRAFFIC kind=3 in_packets=20 in_bytes=4000 out_packets=20 out_bytes=4500",
            "INFO random server log has no counters",
        ]
        c = m.aggregate(lines)
        self.assertEqual(c["3"]["in_packets"], 60)
        self.assertEqual(c["3"]["out_bytes"], 13500)
        self.assertEqual(c["7"]["out_packets"], 900)
        self.assertEqual(len(c), 2)

    def test_coop_reliable_retransmission_and_origins(self):
        lines = [
            "info YT130_COOP_RELIABILITY frames=50 body_bytes=20000"
            " reliable_entries=100 fresh_entries=80 resent_entries=20"
            " ack_only_frames=5 pending_chunks=22 pending_bytes=3300"
            " blocked_members=8 active_members=32",
            "info YT130_COOP_ORIGIN kind=14 sends=90",
            "info YT130_COOP_ORIGIN kind=21 sends=2",
            "info YT130_COOP_RELIABILITY frames=70 body_bytes=30000"
            " reliable_entries=150 fresh_entries=100 resent_entries=50"
            " ack_only_frames=10 pending_chunks=12 pending_bytes=2000"
            " blocked_members=6 active_members=32",
            "info YT130_COOP_ORIGIN kind=14 sends=20",
        ]
        out = m.aggregate_coop(lines)
        self.assertEqual(out["intervals"], 2)
        self.assertEqual(out["metrics"]["reliable_entries"], 250)
        self.assertEqual(out["metrics"]["resent_entries"], 70)
        self.assertEqual(out["metrics"]["ack_only_frames"], 15)
        self.assertEqual(out["metrics"]["pending_chunks"], 22)
        self.assertEqual(out["metrics"]["pending_bytes"], 3300)
        self.assertEqual(out["envelope_body_case_sends"]["14"], 110)

    def test_bad_coop_line_is_not_a_false_interval(self):
        self.assertEqual(m.aggregate_coop([
            "YT130_COOP_RELIABILITY frames=19 secret=password",
            "YT130_COOP_ORIGIN kind=abc sends=2",
        ])["intervals"], 0)

    def test_ignores_malformed_or_unrelated_content(self):
        self.assertEqual(m.aggregate(["YT130_WIRE_TRAFFIC kind=3 in_packets=1 secret=x"]), {})
        self.assertEqual(m.STAGES, (32, 64, 100, 200))


if __name__ == "__main__":
    unittest.main()
