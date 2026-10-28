"""Exact source-only byte counters; retain original game co-op semantics."""
import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).with_name("stage_coop_encoded_bytes.py")
spec = importlib.util.spec_from_file_location("yt_coop_bytes", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class CoopByteStageTests(unittest.TestCase):
    def original(self):
        cpp = "\n".join(new for _, new in m.previous.CPP_PATCHES)
        header = "\n".join(new for _, new in m.previous.H_PATCHES)
        return cpp, header

    def test_encoded_bytes_before_chunking_and_retry(self):
        cpp, header = m.rewrite(*self.original())
        self.assertEqual(cpp.count("EncodeEnvelope(envelope)"), 1)
        self.assertIn("member.stream.Send(encoded, now_ms);", cpp)
        self.assertIn("m_diagEncodedBytes[body_case] += encoded.size();", cpp)
        self.assertIn('" encoded_bytes=" << m_diagEncodedBytes[body_case]', cpp)
        self.assertIn("m_diagEncodedBytes.clear();", cpp)
        self.assertIn("std::map<int, quint64> m_diagEncodedBytes;", header)
        self.assertIn("YT130_COOP_RELIABILITY", cpp)
        self.assertNotIn("online_id", m.NEW_LOG)
        self.assertNotIn("payload", m.NEW_LOG)
        self.assertNotIn("sender", m.NEW_LOG)

    def test_fail_closed_source_revision_and_double_apply(self):
        cpp, header = self.original()
        result = m.rewrite(cpp, header)
        with self.assertRaises(ValueError):
            m.rewrite(*result)
        with self.assertRaises(ValueError):
            m.rewrite(cpp.replace(m.OLD_SEND, "WRONG"), header)
        with self.assertRaises(ValueError):
            m.rewrite(cpp, header.replace(m.OLD_MAP, "WRONG"))

    def test_official_source_is_fixed(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "eca8c30d6fb78099b0f64a52388fd7d65f926e19")
        self.assertEqual(m.BLOBS[m.HEADER], "dfdbd49a30427b71c95e520dbc77498b521bce93")

if __name__ == "__main__":
    unittest.main()
