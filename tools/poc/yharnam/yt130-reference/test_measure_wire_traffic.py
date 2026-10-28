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
        self.assertEqual(out["envelope_type_sends"]["MapBoard"], 110)
        self.assertEqual(out["envelope_type_sends"]["Portrait"], 2)
        self.assertEqual(m.ENVELOPE_NAMES[5], "Entries")
        self.assertEqual(m.ENVELOPE_NAMES[25], "LobbyState")

    def test_encoded_bytes_are_aggregated_separately_from_message_count(self):
        lines = [
            "INFO YT130_COOP_ORIGIN kind=25 sends=10 encoded_bytes=15000",
            "INFO YT130_COOP_ORIGIN kind=25 sends=7 encoded_bytes=13000",
            "INFO YT130_COOP_ORIGIN kind=20 sends=8 encoded_bytes=300",
            # Existing upstream log without byte field must stay readable.
            "INFO YT130_COOP_ORIGIN kind=14 sends=3",
            "INFO YT130_COOP_ORIGIN kind=bad sends=100 encoded_bytes=9999",
        ]
        result = m.aggregate_coop(lines)
        self.assertEqual(result["envelope_type_sends"]["LobbyState"], 17)
        self.assertEqual(result["envelope_type_encoded_bytes"]["LobbyState"], 28000)
        self.assertEqual(result["envelope_type_encoded_bytes"]["VitalsBoard"], 300)
        self.assertEqual(result["envelope_type_sends"]["MapBoard"], 3)
        self.assertNotIn("MapBoard", result["envelope_type_encoded_bytes"])
        self.assertEqual(sum(result["envelope_body_case_encoded_bytes"].values()), 28300)

    def test_qt_world_timer_starvation_source_counters(self):
        source = [
            "INFO YT130_EVENTLOOP read_batches=300 read_datagrams=10000"
            " read_busy_us=500000 max_read_batch_us=120000"
            " max_read_batch_datagrams=800 world_ticks=87"
            " world_busy_us=170000 max_world_busy_us=6200"
            " max_world_gap_us=161000 late_world_ticks=7",
            "INFO YT130_EVENTLOOP read_batches=400 read_datagrams=12000"
            " read_busy_us=600000 max_read_batch_us=60000"
            " max_read_batch_datagrams=900 world_ticks=90"
            " world_busy_us=200000 max_world_busy_us=8000"
            " max_world_gap_us=90000 late_world_ticks=4",
            "YT130_EVENTLOOP player=secret token=unrelated",
        ]
        result = m.aggregate_eventloop(source)
        self.assertEqual(result["observed_windows"], 2)
        c = result["metrics"]
        self.assertEqual(c["read_datagrams"], 22000)
        self.assertEqual(c["read_busy_us"], 1100000)
        self.assertEqual(c["max_read_batch_us"], 120000)
        self.assertEqual(c["max_read_batch_datagrams"], 900)
        self.assertEqual(c["max_world_gap_us"], 161000)
        self.assertEqual(c["late_world_ticks"], 11)
        self.assertEqual(c["world_ticks"], 177)
        self.assertEqual(m.aggregate_coop(source)["eventloop"], result)

    def test_bad_eventloop_rows_fail_closed(self):
        output = m.aggregate_eventloop([
            "YT130_EVENTLOOP read_batches=100 leaking_username=someone",
            "YT130_EVENTLOOP read_batches=x read_datagrams=42",
        ])
        self.assertEqual(output["observed_windows"], 0)
        self.assertEqual(output["metrics"]["read_busy_us"], 0)

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
