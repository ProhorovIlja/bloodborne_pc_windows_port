"""Source exact tests for bounded non-dropping Qt UDP dispatch."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("yt_udp_fairness", HERE / "stage_udp_fairness.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class UdpFairnessSourceTests(unittest.TestCase):
    def original(self):
        return (m.ORIGINAL_READ + "\n" + m.previous.MEASURED_WORLD,
                m.previous.HEADER_NEW)

    def test_bounded_udp_reads_and_lossless_queued_continuation(self):
        cpp, header = m.rewrite(*self.original())
        self.assertIn("if (diag_datagrams >= 128 ||", cpp)
        self.assertIn("busy.nsecsElapsed() >= 2'000'000", cpp)
        self.assertIn("QTimer::singleShot(0, this, [this]", cpp)
        self.assertIn("m_udpContinuationQueued = true;", cpp)
        self.assertIn("m_udpContinuationQueued = false;", cpp)
        self.assertIn("if (m_socket->hasPendingDatagrams() && !m_udpContinuationQueued)", cpp)
        self.assertIn("RecordWire(raw, true)", cpp)
        self.assertIn("HandleLink(raw, sender, senderPort)", cpp)
        self.assertIn("YT130_EVENTLOOP", cpp)
        self.assertNotIn("readAll()", cpp)
        self.assertNotIn("m_socket->close()", cpp)
        self.assertIn("bool m_udpContinuationQueued = false;", header)
        self.assertEqual(cpp.count("++diag_datagrams;"), 1)
        self.assertEqual(cpp.count("while (m_socket->hasPendingDatagrams())"), 1)

    def test_source_drift_and_double_application_fail_closed(self):
        cpp, header = self.original()
        rewritten = m.rewrite(cpp, header)
        with self.assertRaises(ValueError):
            m.rewrite(*rewritten)
        with self.assertRaises(ValueError):
            m.rewrite(cpp.replace("while (m_socket->hasPendingDatagrams())",
                                  "while (false)"), header)
        with self.assertRaises(ValueError):
            m.rewrite(cpp, header.replace(m.HEADER_OLD, "missing"))

    def test_original_instrumentation_blobs_pin_original_yharnam(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8")
        self.assertEqual(m.BLOBS[m.HEADER], "4530df9be35e161cd4e4fd56fe1f1696bb8b407b")
        self.assertIn("RecordWire(raw, true)", m.ORIGINAL_READ)
        self.assertIn("++m_diagReadBatches;", m.ORIGINAL_READ)


if __name__ == "__main__":
    unittest.main()
