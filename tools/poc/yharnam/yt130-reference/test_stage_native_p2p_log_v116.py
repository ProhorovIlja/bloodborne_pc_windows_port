"""V116: source pin, race-safe native packet diagnostic budget, and V115 coupling."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("stage_native_p2p_log_v116.py")
spec=importlib.util.spec_from_file_location("yt130_v116_packet_log",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class NativePacketLogTests(unittest.TestCase):
    @staticmethod
    def sources():
        return (m.MARKER + "\n" + m.INCLUDE_ANCHOR + "\n" + m.ORIGINAL_FN,
                "namespace Libraries::Net::PacketLogBudget {\n"
                "emitted.compare_exchange_weak(seen, seen + 1)")

    def test_preserves_separate_original_3000_log_budgets(self):
        original, helper = self.sources()
        cpp, _ = m.rewrite(original,helper)
        self.assertIn(m.IMPORT,cpp)
        self.assertIn("PacketLogBudget::Take(long_packets_logged, JoinPacketsLogged);",cpp)
        self.assertIn("PacketLogBudget::Take(join_packets_logged, JoinPacketsLogged);",cpp)
        self.assertNotIn("fetch_add(1)",cpp)
        self.assertEqual(cpp.replace(m.REPLACEMENT_FN,m.ORIGINAL_FN).replace(
            m.INCLUDE_ANCHOR+"\n"+m.IMPORT,m.INCLUDE_ANCHOR),original)

    def test_missing_v115_original_drift_duplicate_and_missing_helper_fail_closed(self):
        original, helper=self.sources()
        with self.assertRaisesRegex(ValueError,"V115"):
            m.rewrite(original.replace(m.MARKER,"not installed"),helper)
        with self.assertRaisesRegex(ValueError,"source drift"):
            m.rewrite(original.replace(m.ORIGINAL_FN,"bad"),helper)
        with self.assertRaisesRegex(ValueError,"atomic helper"):
            m.rewrite(original,"unsafe")
        changed=m.rewrite(original,helper)
        with self.assertRaisesRegex(ValueError,"already staged"):
            m.rewrite(*changed)

    def test_original_protocol8_game_blob_locked(self):
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.PINNED_BLOB,"087aef46868b55320f139b3f7c4f46e5fc545347")
        self.assertTrue(m.CPP.endswith("p2p_sockets.cpp"))

if __name__=="__main__":
    unittest.main()
