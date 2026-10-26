"""Pure-source regression tests for the EXPERIMENTAL bounded UDP event loop."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_udp_read_fairness.py")
spec = importlib.util.spec_from_file_location("stage_udp_read_fairness", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class UdpFairnessStageTests(unittest.TestCase):
    def setUp(self):
        self.cpp = "// unrelated source\n" + mod.OLD_METHOD + "\n"
        self.header = "class LinkServer {\n" + mod.OLD_MEMBER + "};\n"

    def test_exact_safe_replacement_preserves_data_handling(self):
        cpp, header = mod.patch_text(self.cpp, self.header)
        for token in ("HandleLink(raw, sender, senderPort);",
                      "m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);",
                      "Busy(busy);", "MaxDatagramsPerTurn = 64",
                      "MaxTurnBusyNs = 2'000'000",
                      "QTimer::singleShot(0, this, [this]",
                      "m_udpDrainQueued = false;"):
            self.assertIn(token, cpp)
        self.assertIn("bool m_udpDrainQueued = false;", header)
        self.assertEqual(cpp.count("HandleLink(raw, sender, senderPort);"), 1)

    def test_refuses_drifted_and_duplicate_source(self):
        for changed_cpp, changed_header in [
            (self.cpp.replace("while (m_socket->hasPendingDatagrams())",
                              "while (true)"), self.header),
            (self.cpp + mod.OLD_METHOD, self.header),
            (self.cpp, self.header.replace("QUdpSocket* m_socket;", "QUdpSocket* raw;")),
            (self.cpp + "m_udpDrainQueued;", self.header),
        ]:
            with self.subTest(changed_cpp=changed_cpp[-80:]):
                with self.assertRaises(ValueError):
                    mod.patch_text(changed_cpp, changed_header)
        patched_cpp, patched_header = mod.patch_text(self.cpp, self.header)
        with self.assertRaises(ValueError):
            mod.patch_text(patched_cpp, patched_header)

    def test_only_expected_upstream_sha_and_files_can_be_modified(self):
        self.assertEqual(len(mod.EXPECTED_BLOBS), 2)
        self.assertEqual(mod.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(set(mod.EXPECTED_BLOBS),
                         {"server/src/link_server.cpp", "server/src/link_server.h"})


if __name__ == "__main__":
    unittest.main()
