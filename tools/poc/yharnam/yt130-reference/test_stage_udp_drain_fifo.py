"""Fail-closed native Qt UDP FIFO fairness stage invariants and privacy."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).with_name("stage_udp_drain_fifo.py")
spec = importlib.util.spec_from_file_location("yt_udp_drain", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class FullDrainTests(unittest.TestCase):
    def original(self):
        # Exact measured production callback prior to new source patch.
        cpp = (m.ORIGINAL_READ + "\n"
               "void LinkServer::HandleLink("
               + "\nvoid LinkServer::OnWorldTick() {\n"
               + m.OLD_EVENTLOG + "\n"
               + m.OLD_RESET + "\n"
               + "YT130_EVENTLOOP")
        h = (m.OLD_INCLUDES + "\n"
             + m.OLD_H + "\n"
             + m.OLD_METHOD_DECL)
        return cpp, h

    def test_receives_all_pending_kernel_datagrams_before_yield(self):
        cpp, header = m.rewrite(*self.original())
        self.assertIn("while (m_socket->hasPendingDatagrams())", cpp)
        self.assertIn("m_udpPending.push_back({std::move(raw), sender, senderPort});", cpp)
        self.assertIn("m_udpPending.pop_front();", cpp)
        self.assertIn("HandleLink(next.bytes, next.sender, next.port);", cpp)
        self.assertIn("if (handled >= 128 ||", cpp)
        self.assertIn("busy.nsecsElapsed() >= 2'000'000", cpp)
        self.assertEqual(cpp.count("QTimer::singleShot(0, this"), 2)
        self.assertIn("void LinkServer::DrainUdpPending()", cpp)
        self.assertIn("void DrainUdpPending();", header)
        self.assertIn("MaxUdpQueuePackets = 16384", header)
        self.assertIn("MaxUdpQueueBytes = 32 << 20", header)
        self.assertIn("std::deque<PendingUdp> m_udpPending", header)
        # Full drain read must not contain a packet-count early return.
        read = cpp.split("void LinkServer::OnReadyRead()", 1)[1].split(
            "void LinkServer::DrainUdpPending()", 1)[0]
        self.assertNotIn("diag_datagrams >=", read)
        self.assertNotIn("break;", read)
        self.assertIn("RecordWire(raw, true)", read)
        self.assertIn("m_udpQueuePressure", cpp)
        self.assertIn("YT130_EVENTLOOP", cpp)

    def test_original_stage_guards_and_no_second_apply(self):
        source = self.original()
        cpp, h = m.rewrite(*source)
        with self.assertRaises(ValueError):
            m.rewrite(cpp, h)
        with self.assertRaises(ValueError):
            m.rewrite(source[0].replace("RecordWire(raw, true)", "disabled"), source[1])
        with self.assertRaises(ValueError):
            m.rewrite(source[0].replace(m.OLD_BODY, "BAD"), source[1])
        with self.assertRaises(ValueError):
            m.rewrite(source[0], source[1].replace(m.OLD_H, "BAD"))

    def test_exact_original_pins(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8")
        self.assertEqual(m.BLOBS[m.HEADER], "4530df9be35e161cd4e4fd56fe1f1696bb8b407b")

if __name__ == "__main__":
    unittest.main()
