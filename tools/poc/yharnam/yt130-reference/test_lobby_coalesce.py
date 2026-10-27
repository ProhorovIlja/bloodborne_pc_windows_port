"""Source guards: coalesce only official lobby broadcast, preserve critical sync."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_lobby_coalesce.py")
spec = importlib.util.spec_from_file_location("yt130_coalesce", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NonHostedCoalesceTests(unittest.TestCase):
    def setUp(self):
        self.source = "\n".join((mod.OLD, mod.TICK, mod.HELLO, mod.TEAM_START))

    def test_only_broadcast_scheduling_changes_not_critical_control(self):
        after = mod.patch_text(self.source)
        self.assertEqual(after.count("lobby_changed = true;"), 1)
        self.assertNotIn("SendLobby(now_ms);\n        }", after)
        self.assertIn(mod.TICK, after)
        self.assertIn(mod.HELLO, after)
        self.assertIn(mod.TEAM_START, after)
        self.assertEqual(after.count("SendTo(member, envelope, now_ms);"), 2)
        with self.assertRaises(ValueError):
            mod.patch_text(after)

    def test_drift_guard_before_any_file_write(self):
        for altered in (self.source.replace("lobby_interval_ms", "different"),
                        self.source + mod.OLD,
                        self.source.replace("if (arrived)", "if (false)"),
                        self.source.replace("TeamStart", "TeamUnknown")):
            with self.subTest(changed=altered[-80:]):
                with self.assertRaises(ValueError):
                    mod.patch_text(altered)

    def test_original_native_source_pin_and_scope(self):
        self.assertEqual(mod.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(mod.BLOB, "eca8c30d6fb78099b0f64a52388fd7d65f926e19")
        self.assertEqual(mod.FILE, "server/src/bloodborne_world.cpp")


if __name__ == "__main__":
    unittest.main()
