"""Stage guards for source pinned Qt UDP callbacks and world tick timings."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_eventloop_timing.py")
spec = importlib.util.spec_from_file_location("yt_evt_timing", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class EventLoopTimingTests(unittest.TestCase):
    def test_original_callbacks_changed_only_by_aggregate_observation(self):
        cpp = mod.ORIGINAL_READ + "\n\n" + mod.ORIGINAL_WORLD
        h = "before\n" + mod.HEADER_ANCHOR + "\nafter"
        changed, header = mod.rewrite(cpp, h)
        self.assertIn("YT130_EVENTLOOP read_batches=", changed)
        self.assertIn("max_world_gap_us=", changed)
        self.assertIn("late_world_ticks=", changed)
        self.assertIn("max_read_batch_us=", changed)
        self.assertIn("m_diagReadDatagrams", header)
        for original in ("HandleLink(raw, sender, senderPort);",
                         "Apply(m_world.Tick(QDateTime::currentMSecsSinceEpoch()));",
                         "FlushRpc(*end);",
                         "while (m_socket->hasPendingDatagrams())",
                         "const qint64 received = m_socket->readDatagram(",
                         "RecordWire(raw, true);",
                         "Busy(busy);"):
            self.assertIn(original, changed)
        for forbidden in ("m_socket->close()", "QTimer::singleShot", "break;",
                          "m_socket->readAll()", "dropDatagram", "m_world.SetHosted"):
            self.assertNotIn(forbidden, changed)
        with self.assertRaises(ValueError):
            mod.rewrite(changed, header)

    def test_unknown_or_repeated_functions_fail_closed(self):
        good = mod.ORIGINAL_READ + "\n" + mod.ORIGINAL_WORLD
        h = mod.HEADER_ANCHOR
        for bad in ("", good + mod.ORIGINAL_READ,
                    good.replace("while (m_socket->hasPendingDatagrams())",
                                 "while (true)"),
                    good.replace("FlushRpc(*end);", "FlushRpc(null);")):
            with self.subTest(bad=bad[-80:]):
                with self.assertRaises(ValueError):
                    mod.rewrite(bad, h)

    def test_pin_metadata(self):
        self.assertEqual(mod.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(mod.CPP_BLOB, "b5c9bdcfcbfe6730689ae70459e85775bb1d8dc8")
        self.assertEqual(mod.HEADER_BLOB, "4530df9be35e161cd4e4fd56fe1f1696bb8b407b")


if __name__ == "__main__":
    unittest.main()
