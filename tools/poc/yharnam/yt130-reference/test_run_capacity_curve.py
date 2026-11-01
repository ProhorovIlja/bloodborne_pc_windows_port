"""Synthetic test data only; real game/CPU measurements are generated in GitHub CI."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).with_name("run_capacity_curve.py")
sp=importlib.util.spec_from_file_location("yt130_capacity",p)
mod=importlib.util.module_from_spec(sp)
sp.loader.exec_module(mod)
class CapacityUnitTests(unittest.TestCase):
    def test_expected_steps_and_admission_ramp(self):
        self.assertEqual(mod.STAGES,(4,16,32,64,100,200))
        self.assertEqual(mod.DIAGNOSTIC_STAGES,(32,64,100,200))
        for n in mod.STAGES:
            processes,seconds,ramp=mod.settings(n)
            self.assertGreaterEqual(processes,1)
            self.assertLessEqual(processes,4)
            self.assertGreaterEqual(seconds,15)
            self.assertGreaterEqual(ramp,100)
        with self.assertRaises(ValueError):
            mod.settings(10000)
    def test_true_delivery_and_valid_packets_required(self):
        baseline = {"players":200, "playing":200,
                    "packets_sent":2000, "packets_received":2000,
                    "packets_lost":0, "relay_ms_p99":0.7,
                    "main_thread_cpu_avg":5.0}
        self.assertEqual(mod.quality(baseline, 200), "FULL_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"playing":199}, 200), "PARTIAL_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"players":199}, 200), "GENERATOR_MISMATCH")
        self.assertEqual(mod.quality(baseline | {"playing":0}, 200), "NO_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"packets_received":0}, 200), "NO_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"packets_received":1}, 200),
                         "INSUFFICIENT_DELIVERY_EVIDENCE")
        self.assertEqual(mod.quality(baseline | {"packets_sent":1, "packets_received":1}, 200),
                         "INSUFFICIENT_DELIVERY_EVIDENCE")
        # Original bbload serializes QJsonObject counters as double values.
        self.assertEqual(mod.quality(baseline | {"packets_sent":2000.0,
                                                 "packets_received":2000.0}, 200),
                         "FULL_GAMEPLAY")
        # Broadcast/fan-out and detected sequence gaps do not prove corruption.
        self.assertEqual(mod.quality(baseline | {"packets_received":3000}, 200),
                         "FULL_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"packets_received":1900}, 200),
                         "DELIVERY_DEGRADED")
        self.assertEqual(mod.quality(baseline | {"relay_ms_p99":262.676}, 200),
                         "RELAY_LATENCY_DEGRADED")
        self.assertEqual(mod.quality(baseline | {"main_thread_cpu_avg":84.1}, 200),
                         "MAIN_THREAD_SATURATED")
        # Actual six-stage optimized 2026-10-26 synthetic evidence,
        # without inventing per-client packet delivery.
        actual64 = baseline | {"players":64, "playing":64, "packets_sent":40714,
                               "packets_received":39882, "packets_lost":787,
                               "relay_ms_p99":262.676,"main_thread_cpu_avg":18.6}
        actual100 = baseline | {"players":100, "playing":100, "packets_sent":54435,
                                "packets_received":32951, "packets_lost":19277,
                                "relay_ms_p99":2859.115, "main_thread_cpu_avg":84.1}
        self.assertEqual(mod.quality(actual64, 64), "DELIVERY_DEGRADED")
        self.assertEqual(mod.quality(actual100, 100), "DELIVERY_DEGRADED")
        for bad in ({"playing":201}, {"packets_sent":float("nan")},
                    {"packets_received":True}, {"packets_received":-1},
                    {"packets_received":None}, {"packets_received":3.5},
                    {"packets_sent":float("inf")}):
            with self.subTest(bad=bad):
                self.assertEqual(mod.quality(baseline | bad, 200), "INVALID_METRICS")

if __name__=="__main__":
    unittest.main()
