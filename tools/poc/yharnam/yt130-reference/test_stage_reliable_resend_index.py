"""Source-pinned native C++ reliable resend cost and behavior safety tests."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).with_name("stage_reliable_resend_index.py")
spec = importlib.util.spec_from_file_location("pinned_resend", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeReliableResendTests(unittest.TestCase):
    def original(self):
        header = "\n".join((m.OLD_INCLUDE, m.OLD_ENTRY, m.OLD_LOOKUP,\n                            "                out.wait_ms = (std::min)(out.wait_ms * 2, settings.max_resend_ms);",\n                            m.OLD_RESEND))
        test = "// NonHostedTeamEditsAreCoalescedAndStartStillWorks\n" + m.OLD_TEST
        return header, test

    def test_preserves_reliable_fresh_and_resend_accounting(self):
        header, cpp = m.rewrite(*self.original())
        self.assertIn("std::set<u32> emitted_reliable;", header)
        self.assertIn("emitted_reliable.insert(out.seq);", header)
        self.assertIn("!emitted_reliable.contains(seq)", header)
        self.assertIn("emitted_reliable.insert(seq);", header)
        self.assertIn("++resends;", header)
        self.assertIn("++resent;", header)
        self.assertIn("out.wait_ms = (std::min)(out.wait_ms * 2", header)
        self.assertNotIn("std::ranges::none_of(entries", header)
        self.assertIn("GameLinkBurstResendSequenceDedupAndAck", cpp)
        self.assertIn("CHECK(retry_seq.size() == 64)", cpp)
        self.assertIn("CHECK(sender.Unacked() == 0)", cpp)

    def test_drift_missing_prior_stage_and_repeat_rejected(self):
        old = self.original()
        changed = m.rewrite(*old)
        with self.assertRaises(ValueError):
            m.rewrite(*changed)
        with self.assertRaises(ValueError):
            m.rewrite(old[0], m.OLD_TEST)
        with self.assertRaises(ValueError):
            m.rewrite(old[0].replace("std::ranges::none_of", "std::ranges::any_of"),
                      old[1])
        with self.assertRaises(ValueError):
            m.rewrite(old[0], old[1] + m.OLD_TEST)

    def test_exact_official_original_blobs_only(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.HEADER], "5029581251bfe5decf562c19a10bdd079150cdad")
        self.assertEqual(m.BLOBS[m.TEST], "2ec55d02101545723e9889bebe83d8b1d531a1c7")


if __name__ == "__main__":
    unittest.main()
