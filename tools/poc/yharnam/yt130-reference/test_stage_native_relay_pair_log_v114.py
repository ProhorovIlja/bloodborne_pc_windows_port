"""Fail-closed source tests for real Qt UDP relay debug bookkeeping fast path."""
import importlib.util
from pathlib import Path
import unittest


p = Path(__file__).with_name("stage_native_relay_pair_log_v114.py")
spec = importlib.util.spec_from_file_location("yt_v114_relay_pair_log", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class OriginalNativeRelayTests(unittest.TestCase):
    @staticmethod
    def source():
        return {
            m.LINK_H: "start\n" + m.HEADER_OLD + "\nend\n",
            m.HUB_CPP: ("start\n" +
                        "// SHYT-V108-MULTI-INVADER-ORIGINAL-SERVER\n" +
                        m.HUB_OLD + "\nend\n"),
            m.HUB_TEST: "start\n" + m.TEST_ANCHOR + "\nend\n",
        }

    def test_fastpath_bypasses_only_pair_debug_without_changing_game_relay(self):
        original = self.source()
        changed = m.rewrite(original)
        self.assertIn("ServerLink::Hub m_link{3000, 60000, 10000, 0, 12000};",
                      changed[m.LINK_H])
        self.assertIn("if (pair_lines > 0) {", changed[m.HUB_CPP])
        self.assertIn("++pair_frames[qMakePair(", changed[m.HUB_CPP])
        self.assertIn("result.log.append(QStringLiteral(", changed[m.HUB_CPP])
        # Dispatch, Route, authenticated Link data are outside this source
        # anchor; replacing only the debug lines leaves all other bytes.
        self.assertEqual(
            changed[m.HUB_CPP].replace(m.HUB_NEW, m.HUB_OLD),
            original[m.HUB_CPP])
        self.assertIn("Net no_pair_debug(3000, 60000, 10000, 0);",
                      changed[m.HUB_TEST])
        self.assertIn("index < 100;", changed[m.HUB_TEST])
        self.assertIn("delivered.size() == 1", changed[m.HUB_TEST])
        self.assertIn("sample.log.isEmpty()", changed[m.HUB_TEST])
        self.assertIn("no_pair_debug.unopened == 0", changed[m.HUB_TEST])
        self.assertEqual(changed[m.LINK_H].count(m.MARKER), 1)

    def test_fails_closed_on_absent_anchor_or_second_patch(self):
        source = self.source()
        for path, old in ((m.LINK_H, m.HEADER_OLD),
                          (m.HUB_CPP, m.HUB_OLD),
                          (m.HUB_TEST, m.TEST_ANCHOR)):
            changed = dict(source)
            changed[path] = changed[path].replace(old, "BROKEN", 1)
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "anchor drift"):
                    m.rewrite(changed)
        with self.assertRaisesRegex(ValueError, "twice"):
            m.rewrite(m.rewrite(source))
        with self.assertRaisesRegex(ValueError, "all three"):
            m.rewrite({m.HUB_CPP: source[m.HUB_CPP]})

    def test_pinned_actual_qt_source_ids(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.LINK_H],
                         "4530df9be35e161cd4e4fd56fe1f1696bb8b407b")
        self.assertEqual(m.BLOBS[m.HUB_CPP],
                         "eca0980de1e72177c38e1a0e3e613e9a97f13442")
        self.assertEqual(m.BLOBS[m.HUB_TEST],
                         "454f5575dcfe1b45ee56b0b42353f34aaee2556d")


if __name__ == "__main__":
    unittest.main()
