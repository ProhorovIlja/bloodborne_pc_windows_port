"""Fail-closed guards: retransmit scan removal keeps original ACK/backoff/limits."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).with_name("stage_reliable_resend_noscan.py")
spec = importlib.util.spec_from_file_location("yt_resend_noscan", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ReliableNoScanTests(unittest.TestCase):
    def original(self):
        head = ("    s64 resend_ms = 150;\n"
                "    size_t max_resends = 64;\n" +
                m.FRESH_INVARIANT + "\n" + m.OLD_SCAN)
        test = ("// NonHostedTeamEditsAreCoalescedAndStartStillWorks\n" +
                m.OLD_TEST)
        return head, test

    def test_unchanged_wire_retry_ack_and_limit(self):
        head, test = m.rewrite(*self.original())
        self.assertNotIn("std::ranges::none_of(entries", head)
        self.assertIn("if (now_ms - out.sent_ms >= out.wait_ms)", head)
        self.assertIn(m.FRESH_INVARIANT, head)
        self.assertIn("size_t max_resends = 64;", head)
        self.assertIn("GameLinkBurstResendSequenceDedupAndAck", test)
        self.assertIn("CHECK(retry_seq.size() == 64)", test)
        self.assertIn("CHECK(sender.Unacked() == 0)", test)
        self.assertIn("CHECK(delivered == 320)", test)

    def test_reject_duplicate_and_missing_original_invariants(self):
        head, test = self.original()
        changed = m.rewrite(head, test)
        with self.assertRaises(ValueError):
            m.rewrite(*changed)
        with self.assertRaises(ValueError):
            m.rewrite(head.replace("out.sent_ms = now_ms;", "out.sent_ms = 0;"), test)
        with self.assertRaises(ValueError):
            m.rewrite(head.replace("size_t max_resends = 64;", "size_t max_resends = 4096;"), test)
        with self.assertRaises(ValueError):
            m.rewrite(head, m.OLD_TEST)
        with self.assertRaises(ValueError):
            m.rewrite(head.replace(m.OLD_SCAN, "return;"), test)

    def test_exact_upstream_pin_no_unverified_backport(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.HEADER], "5029581251bfe5decf562c19a10bdd079150cdad")
        self.assertEqual(m.BLOBS[m.TEST], "2ec55d02101545723e9889bebe83d8b1d531a1c7")

if __name__ == "__main__":
    unittest.main()
