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
    def test_no_200_player_success_when_no_one_plays(self):
        self.assertEqual(mod.quality({"players":200,"playing":0,"packets_sent":0},200),"NO_GAMEPLAY")
        self.assertEqual(mod.quality({"players":200,"playing":199,"packets_sent":300},200),"PARTIAL_GAMEPLAY")
        self.assertEqual(mod.quality({"players":200,"playing":200,"packets_sent":300},200),"FULL_GAMEPLAY")
        self.assertEqual(mod.quality({"players":199,"playing":199,"packets_sent":300},200),"GENERATOR_MISMATCH")
if __name__=="__main__":
    unittest.main()
