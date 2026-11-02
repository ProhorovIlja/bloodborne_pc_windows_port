"""Exact source anchor, QoS-free and privacy guard tests for CoopStream profiler."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name("stage_coop_reliability.py")
spec = importlib.util.spec_from_file_location("coop_reliability", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CoopReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.cpp = "\nUNRELATED\n".join(old for old, _ in mod.CPP_PATCHES)
        self.h = "\nUNRELATED\n".join(old for old, _ in mod.H_PATCHES)

    def test_source_exact_and_reversible_enough_to_reject_duplicate(self):
        cpp, header = mod.patch_text(self.cpp, self.h)
        self.assertIn("YT130_COOP_RELIABILITY frames=", cpp)
        self.assertIn("YT130_COOP_ORIGIN kind=", cpp)
        self.assertIn("void Service::ReportDiagnostics(qint64 now_ms)", cpp)
        self.assertIn("void Service::CountDiagnosticFrame(const std::vector<u8>& body)", cpp)
        self.assertIn("++m_diagEnvelopes[static_cast<int>(envelope.body_case())]", cpp)
        self.assertIn("m_diagResends += member->stream.Resends() - before_resends;", cpp)
        self.assertIn("m_diagResends += member.stream.Resends() - before_resends;", cpp)
        self.assertEqual(cpp.count("CountDiagnosticFrame(body);"), 2)
        self.assertIn("std::map<int, quint64> m_diagEnvelopes;", header)
        self.assertIn("void CountDiagnosticFrame(const std::vector<u8>& body);", header)
        with self.assertRaises(ValueError):
            mod.patch_text(cpp, header)

    def test_missing_duplicate_or_modified_anchor_aborts(self):
        self.assertEqual(mod.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(set(mod.BLOBS), {
            "server/src/bloodborne_world.cpp", "server/src/bloodborne_world.h"})
        for broken in (self.cpp.replace("member->stream.Flush", "BAD.Flush"),
                       self.cpp + mod.CPP_PATCHES[1][0],
                       self.cpp.replace("Flush(now_ms, result);", "Flush(now_ms+1, result);")):
            with self.subTest(broken=broken[-60:]):
                with self.assertRaises(ValueError):
                    mod.patch_text(broken, self.h)
        with self.assertRaises(ValueError):
            mod.patch_text(self.cpp, self.h + mod.H_PATCHES[0][0])

    def test_no_affects_to_reliability_authority_or_pii_in_logs(self):
        cpp, header = mod.patch_text(self.cpp, self.h)
        # No replacement, deletion or renumbering of original Send, Flush,
        # auth, party or world handlers; instrumentation only.
        self.assertIn("member.stream.Send(EncodeEnvelope(envelope), now_ms);", cpp)
        self.assertIn("member->stream.Flush(now_ms)", cpp)
        self.assertIn("member.stream.Flush(now_ms)", cpp)
        marker = cpp.split('<< "YT130_COOP_RELIABILITY frames="', 1)[1]
        marker = marker.split("m_diagAt = now_ms;", 1)[0]
        # Only executable QDebug expressions matter: ordinary comments
        # mentioning excluded fields are not emitted into the runtime log.
        marker = "\n".join(line for line in marker.splitlines()
                           if not line.lstrip().startswith("//"))
        for secret_field in ('online_id', 'password', 'secret', 'packet_body',
                             'member.name', 'toString()', 'toHex()'):
            self.assertNotIn(secret_field, marker)
        self.assertIn('pending_bytes=', marker)


if __name__ == "__main__":
    unittest.main()
