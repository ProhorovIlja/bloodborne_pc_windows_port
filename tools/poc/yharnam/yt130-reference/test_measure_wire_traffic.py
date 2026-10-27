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

    def test_ignores_malformed_or_unrelated_content(self):
        self.assertEqual(m.aggregate(["YT130_WIRE_TRAFFIC kind=3 in_packets=1 secret=x"]), {})
        self.assertEqual(m.STAGES, (32, 64, 100, 200))


if __name__ == "__main__":
    unittest.main()
