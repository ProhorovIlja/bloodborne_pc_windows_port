"""V125 exact-original Qt read callback regression; no capacity claim."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest
import stage_eventloop_timing as timing

spec = importlib.util.spec_from_file_location(
    "yt130_udp_fair", Path(__file__).with_name("stage_udp_fair_read_v125.py"))
assert spec and spec.loader
fair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fair)


class FairReadTests(unittest.TestCase):
    def setUp(self):
        self.cpp = timing.MEASURED_READ + "\n" + timing.MEASURED_WORLD
        self.header = timing.HEADER_NEW

    def test_preserves_real_datagram_wire_dispatch_and_world_tick(self):
        cpp, header = fair.rewrite(self.cpp, self.header)
        self.assertEqual(cpp.count("readDatagram("), self.cpp.count("readDatagram("))
        self.assertIn("RecordWire(raw, true)", cpp)
        self.assertIn("HandleLink(raw, sender, senderPort)", cpp)
        self.assertIn("Apply(m_world.Tick", cpp)
        self.assertLess(cpp.index("if (diag_datagrams >= 64"), cpp.index("QByteArray raw;"))
        self.assertIn("m_udpFairContinuationPending = false", header)
        self.assertIn('<< " read_yields=" << m_diagReadYields', cpp)
        self.assertIn("m_diagReadYields = 0;", cpp)

    def test_timer_has_receiver_context_and_one_pending_instance(self):
        cpp, _ = fair.rewrite(self.cpp, self.header)
        self.assertIn("if (!m_udpFairContinuationPending)", cpp)
        self.assertEqual(cpp.count("QTimer::singleShot(1, this, [this]"), 1)
        self.assertIn("m_udpFairContinuationPending = false;\n                    OnReadyRead();", cpp)
        self.assertEqual(fair.CONTINUATION_DELAY_MS, 1)

    def test_rejects_duplicate_and_drifted_sources(self):
        cpp, header = fair.rewrite(self.cpp, self.header)
        with self.assertRaises(ValueError):
            fair.rewrite(cpp, header)
        with self.assertRaises(ValueError):
            fair.rewrite(self.cpp.replace("while (m_socket->hasPendingDatagrams())",
                                              "while (false)"), self.header)
        with self.assertRaises(ValueError):
            fair.rewrite(self.cpp, self.header.replace("m_diagReadBatches", "unknown"))

    def test_explicit_budget_and_no_drop_logic(self):
        self.assertEqual((fair.MAX_DATAGRAMS, fair.MAX_READ_US), (64, 2000))
        self.assertNotIn("dropDatagram", fair.LOOP_REPLACEMENT)
        self.assertNotIn("DirectP2P", fair.LOOP_REPLACEMENT)


if __name__ == "__main__":
    unittest.main()
