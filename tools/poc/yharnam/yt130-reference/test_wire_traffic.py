"""Strict source anchor and no-payload logging guards for wire instrumentation."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).with_name("stage_wire_traffic.py")
spec = importlib.util.spec_from_file_location("wire", p)
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)


class WireSourceTests(unittest.TestCase):
    def test_pinned_source_only(self):
        self.assertEqual(wire.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(set(wire.BLOBS), {
            "server/src/link_server.cpp", "server/src/link_server.h"})

    def test_every_exact_anchor_one_time(self):
        cpp = "head\n" + "\n".join(old for old, _ in wire.PATCHES_CPP) + "\n"
        hdr = "head\n" + "\n".join(old for old, _ in wire.PATCHES_HEADER) + "\n"
        changed_cpp, changed_h = wire.patch_text(cpp, hdr)
        self.assertIn("YT130_WIRE_TRAFFIC kind=", changed_cpp)
        self.assertIn("m_wireInPackets", changed_h)
        self.assertEqual(changed_cpp.count("RecordWire(send.datagram, false)"), 1)
        self.assertEqual(changed_cpp.count("RecordWire(*sealed, false)"), 1)
        self.assertEqual(changed_cpp.count("RecordWire(raw, true)"), 1)
        with self.assertRaises(ValueError):
            wire.patch_text(changed_cpp, changed_h)
        with self.assertRaises(ValueError):
            wire.patch_text(cpp.replace("m_link.Tick", "m_other.Tick"), hdr)
        with self.assertRaises(ValueError):
            wire.patch_text(cpp, hdr.replace("QUdpSocket* m_socket", "QUdpSocket* bad"))

    def test_no_secrets_or_identifiers_in_traffic_log(self):
        source = "\n".join(new for _, new in wire.PATCHES_CPP)
        line = source.split('<< "YT130_WIRE_TRAFFIC kind="', 1)[1].split(";", 1)[0]
        self.assertNotIn("online_id", line)
        self.assertNotIn("datagram", line)
        self.assertNotIn("sender", line)
        self.assertNotIn("payload", line)
        self.assertIn("in_bytes=", line)
        self.assertIn("out_bytes=", line)


if __name__ == "__main__":
    unittest.main()
