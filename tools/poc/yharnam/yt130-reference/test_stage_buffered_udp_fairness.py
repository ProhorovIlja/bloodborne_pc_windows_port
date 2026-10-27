"""Original Qt UDP processing must remain source-accurate and FIFO."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "yt130_buffered_udp", HERE / "stage_buffered_udp_fairness.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
import stage_eventloop_timing as prior


class BufferedUdpTests(unittest.TestCase):
    def test_on_ready_read_always_drains_socket_and_retains_wire_count(self):
        cpp = prior.MEASURED_READ + "\n\n" + prior.MEASURED_WORLD
        header = ("#include <map>\n" + "private slots:\n    void OnReadyRead();\n"
                  + prior.HEADER_NEW)
        result, h = m.patch_text(cpp, header)
        self.assertIn("while (m_socket->hasPendingDatagrams())", result)
        self.assertIn("RecordWire(raw, true)", result)
        self.assertIn("if (ServerLink::KindOf(raw))", result)
        self.assertIn("m_udpPending.push_back(", result)
        self.assertIn("HandleLink(item.body, item.sender, item.port)", result)
        self.assertNotIn("HandleLink(raw, sender, senderPort)", result)
        self.assertIn("std::deque<QueuedUdp>", h)
        self.assertIn("QTimer::singleShot(1, this,", result)
        self.assertIn("handled < 128", result)
        self.assertIn("work.nsecsElapsed() < 2'000'000LL", result)
        self.assertIn("m_udpPendingBytes + needed > 32LL * 1024 * 1024", result)
        self.assertIn("YT130_UDP_FAIR_QUEUE slices=", result)
        self.assertIn("overload_drops=", result)
        self.assertIn("void DrainPendingUdp();", h)
        self.assertIn("Apply(m_world.Tick(QDateTime::currentMSecsSinceEpoch()))", result)
        self.assertNotIn("m_socket->close()", result)
        self.assertNotIn("m_world.SetHosted", result)
        self.assertNotIn("ServerLink::KindOf(raw)) {\n            HandleLink(", result)

    def test_no_double_stage_and_unknown_source_fails_closed(self):
        cpp = prior.MEASURED_READ + "\n\n" + prior.MEASURED_WORLD
        header = ("#include <map>\n    void OnReadyRead();\n" +
                  prior.HEADER_NEW)
        staged, staged_h = m.patch_text(cpp, header)
        with self.assertRaises(ValueError):
            m.patch_text(staged, staged_h)
        with self.assertRaises(ValueError):
            m.patch_text(cpp.replace("RecordWire(raw, true)", "RecordWire(raw, false)"),
                         header)
        with self.assertRaises(ValueError):
            m.patch_text(cpp, header.replace("Database m_db;", "Database other;"))
        with self.assertRaises(ValueError):
            m.patch_text(cpp + prior.MEASURED_READ, header)

    def test_original_blob_pins_are_intact(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.CPP_BLOB, "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8")
        self.assertEqual(m.HEADER_BLOB, "4530df9be35e161cd4e4fd56fe1f1696bb8b407b")


if __name__ == "__main__":
    unittest.main()
