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

    def test_fifo_qt_eventloop_counters_keep_read_and_world_timing(self):
        rows = [
            "INFO YT130_EVENTLOOP read_batches=200 udp_queue_max=300 udp_queue_pressure=4"
            " read_datagrams=8000 read_busy_us=400000 max_read_batch_us=67000"
            " max_read_batch_datagrams=500 world_ticks=95"
            " world_busy_us=170000 max_world_busy_us=6200"
            " max_world_gap_us=81000 late_world_ticks=3",
            "INFO YT130_EVENTLOOP read_batches=100 udp_queue_max=420 udp_queue_pressure=9"
            " read_datagrams=9000 read_busy_us=500000 max_read_batch_us=40000"
            " max_read_batch_datagrams=600 world_ticks=97"
            " world_busy_us=90000 max_world_busy_us=4000"
            " max_world_gap_us=75000 late_world_ticks=1",
            "INFO YT130_EVENTLOOP read_batches=100 udp_queue_max=bad udp_queue_pressure=0"
            " read_datagrams=2 read_busy_us=1 max_read_batch_us=1"
            " max_read_batch_datagrams=1 world_ticks=1"
            " world_busy_us=1 max_world_busy_us=1 max_world_gap_us=1 late_world_ticks=1",
        ]
        evidence = m.aggregate_eventloop(rows)
        self.assertEqual(evidence["observed_windows"], 2)
        self.assertEqual(evidence["queue_evidence_windows"], 2)
        metrics = evidence["metrics"]
        self.assertEqual(metrics["udp_queue_max"], 420)
        self.assertEqual(metrics["udp_queue_pressure"], 13)
        self.assertEqual(metrics["read_batches"], 300)
        self.assertEqual(metrics["read_datagrams"], 17000)
        self.assertEqual(metrics["max_read_batch_us"], 67000)
        self.assertEqual(metrics["world_ticks"], 192)
        self.assertEqual(metrics["max_world_gap_us"], 81000)
        self.assertEqual(metrics["late_world_ticks"], 4)
        # CRITICAL: the 5s source logs are accepted unchanged by
        # the same Coop diagnostic parser consumed in CI artifacts.
        self.assertEqual(m.aggregate_coop(rows)["eventloop"], evidence)

    def test_legacy_eventloop_is_readable_but_fifo_evidence_missing(self):
        row = ("YT130_EVENTLOOP read_batches=9 read_datagrams=12"
               " read_busy_us=100 max_read_batch_us=80"
               " max_read_batch_datagrams=7 world_ticks=10"
               " world_busy_us=40 max_world_busy_us=20"
               " max_world_gap_us=55 late_world_ticks=1")
        got = m.aggregate_eventloop([row])
        self.assertEqual(got["observed_windows"], 1)
        self.assertEqual(got["queue_evidence_windows"], 0)
        self.assertEqual(got["metrics"]["udp_queue_max"], 0)
        self.assertEqual(got["metrics"]["read_datagrams"], 12)

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
