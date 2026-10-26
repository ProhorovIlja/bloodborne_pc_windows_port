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
                    "packets_lost":0}
        self.assertEqual(mod.quality(baseline, 200), "FULL_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"playing":199}, 200), "PARTIAL_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"players":199}, 200), "GENERATOR_MISMATCH")
        self.assertEqual(mod.quality(baseline | {"playing":0}, 200), "NO_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"packets_received":0}, 200), "NO_GAMEPLAY")
        self.assertEqual(mod.quality(baseline | {"packets_received":1}, 200),
                         "INSUFFICIENT_DELIVERY_EVIDENCE")
        self.assertEqual(mod.quality(baseline | {"packets_sent":1, "packets_received":1}, 200),
                         "INSUFFICIENT_DELIVERY_EVIDENCE")
        for bad in ({"packets_received":2001}, {"packets_lost":2001},
                    {"packets_sent":float("nan")}, {"packets_received":True},
                    {"packets_received":-1}, {"packets_received":None}):
            with self.subTest(bad=bad):
                self.assertEqual(mod.quality(baseline | bad, 200), "INVALID_METRICS")

if __name__=="__main__":
    unittest.main()
