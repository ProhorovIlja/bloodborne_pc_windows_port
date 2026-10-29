"""Test exact source-guard patch: REAL native YT1.3 Protocol8 game receive queue."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_native_rx_queue_v115.py")
spec = importlib.util.spec_from_file_location("yt130_native_rx_v115", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NativeRxQueueSource(unittest.TestCase):
    @staticmethod
    def fixtures():
        return (m.ANCHOR_INCLUDE + "\n" + m.ANCHOR_CONSUMED + "\n" +
                m.ANCHOR_PUSH,
                m.ANCHOR_MEMBER,
                "namespace Libraries::Net::RxBudget {\n"
                "inline constexpr std::size_t MaxPayloadBytes = 8 * 1024 * 1024;")

    def test_real_original_cpp_is_wired_to_bounded_header(self):
        cpp, sock, helper = m.rewrite(*self.fixtures())
        self.assertIn(m.IMPORT, cpp)
        self.assertIn("RxBudget::Enqueue(receive_queue, receive_queued_bytes", cpp)
        self.assertIn("RxBudget::Consumed(receive_queue.front(), receive_queued_bytes)", cpp)
        self.assertIn("receive_queued_bytes{0}", sock)
        self.assertIn("receive_dropped_packets{0}", sock)
        self.assertIn("if (!inserted.accepted)\n        return;", cpp)
        self.assertEqual(cpp.count("receive_queue.push_back"), 0)
        self.assertIn("transport loss is possible", cpp)
        self.assertEqual(sock.count(m.MARKER), 1)
        self.assertIn("namespace Libraries::Net::RxBudget", helper)

    def test_reject_drift_duplicate_and_untrusted_helper(self):
        cpp, sock, helper = self.fixtures()
        for fragment in (m.ANCHOR_INCLUDE, m.ANCHOR_CONSUMED, m.ANCHOR_PUSH):
            with self.subTest(fragment=fragment):
                with self.assertRaisesRegex(ValueError, "anchor drift"):
                    m.rewrite(cpp.replace(fragment, "BROKEN", 1), sock, helper)
        with self.assertRaisesRegex(ValueError, "anchor drift"):
            m.rewrite(cpp, sock.replace(m.ANCHOR_MEMBER, "BROKEN"), helper)
        with self.assertRaisesRegex(ValueError, "native helper"):
            m.rewrite(cpp, sock, "unsafe")
        changed = m.rewrite(cpp, sock, helper)
        with self.assertRaisesRegex(ValueError, "repeated"):
            m.rewrite(*changed)

    def test_original_network_git_blobs_exact(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "087aef46868b55320f139b3f7c4f46e5fc545347")
        self.assertEqual(m.BLOBS[m.SOCKETS],
                         "5e4636ee0b4c67a849f8d45c6bf50e590f27c87e")


if __name__ == "__main__":
    unittest.main()
