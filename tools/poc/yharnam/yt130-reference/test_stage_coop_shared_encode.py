"""Original native Coop7 broadcast encoding reuse must preserve per-peer streams."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).with_name("stage_coop_shared_encode.py")
spec = importlib.util.spec_from_file_location("yt_coop7_shared_encode", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class SharedEncodeTests(unittest.TestCase):
    def original(self):
        cpp = "\n".join((
            "YT130_COOP_RELIABILITY",
            m.SEND_BEFORE, m.ENTRY_BEFORE, m.BOARD_BEFORE,
        ))
        header = "m_diagEnvelopes\n" + m.H_BEFORE
        cpp_test = ("int NonHostedTeamEditsAreCoalescedAndStartStillWorks() { return 0; }\n" +
                    m.TEST_ANCHOR)
        return cpp, header, cpp_test

    def test_wires_and_destination_streams_remain_individual(self):
        cpp, header, tests = m.rewrite(*self.original())
        self.assertIn("member.stream.Send(bytes, now_ms);", cpp)
        self.assertIn("++m_diagEnvelopes[body_case];", cpp)
        self.assertIn("if (!member.to_flush)", cpp)
        self.assertIn("flush_now.push_back(&member);", cpp)
        self.assertIn("SendEncoded(member, *encoded", cpp)
        self.assertEqual(cpp.count("SendEncoded(member, *encoded"), 2)
        self.assertEqual(cpp.count("std::optional<std::vector<u8>> encoded;"), 2)
        self.assertEqual(cpp.count("encoded = EncodeEnvelope("), 2)
        self.assertIn("SendTo(*only, board, now_ms)", cpp)
        self.assertIn("if (member.party == world.name)", cpp)
        self.assertIn("void SendEncoded(Member& member", header)
        self.assertIn("IdenticalCoopBroadcastsKeepPartyWorldAndReliableDelivery", tests)
        self.assertIn('outsider.Hello(now, "other:isolated")', tests)
        self.assertIn("CHECK(!Killed(outsider, 0x10014066));", tests)
        self.assertIn("CHECK(guest.vitals_board.members_size() >= 2);", tests)

    def test_refuse_unexpected_or_double_staged_sources(self):
        base = self.original()
        output = m.rewrite(*base)
        with self.assertRaises(ValueError):
            m.rewrite(*output)
        for n, fragment in enumerate((m.SEND_BEFORE, m.H_BEFORE, m.TEST_ANCHOR)):
            x = list(base)
            x[n] = x[n].replace(fragment, "MISMATCH")
            with self.subTest(source=n), self.assertRaises(ValueError):
                m.rewrite(*x)
        with self.assertRaises(ValueError):
            m.rewrite(base[0].replace(m.BOARD_BEFORE, "BAD"), base[1], base[2])
        with self.assertRaises(ValueError):
            m.rewrite(base[0].replace(m.ENTRY_BEFORE, "BAD"), base[1], base[2])

    def test_official_v130_commit_and_blobs(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "eca8c30d6fb78099b0f64a52388fd7d65f926e19")
        self.assertEqual(m.BLOBS[m.HEADER], "dfdbd49a30427b71c95e520dbc77498b521bce93")
        self.assertEqual(m.BLOBS[m.TEST], "2ec55d02101545723e9889bebe83d8b1d531a1c7")

if __name__ == "__main__":
    unittest.main()
