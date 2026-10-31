"""V181 synthetic and pinned-source Qt UDP socket guard tests; no retail files."""
from pathlib import Path
import importlib.util
import unittest

p = Path(__file__).with_name("stage_qt_udp_readback_v181.py")
spec = importlib.util.spec_from_file_location("yt181_udp", p)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def source_fixture():
    return (
        "// Original pinned Qt LinkServer methods, fake external context.\n"
        "bool LinkServer::Start(const QHostAddress& addr, uint16_t port) {\n"
        + v.BUFF_OLD + "\n}\n"
        "void LinkServer::OnReadyRead() {\n"
        + v.READ_OLD + "\n}\n"
    )


class UdpReadbackGuardTests(unittest.TestCase):
    def test_preserve_actual_socket_options_and_show_effective_capped_values(self):
        patched = v.patch(source_fixture())
        self.assertEqual(patched.count(v.MARK), 1)
        self.assertEqual(patched.count("setSocketOption("), 2)
        self.assertEqual(patched.count("socketOption("), 2)
        self.assertIn("effective_receive_bytes=", patched)
        self.assertIn("effective_send_bytes=", patched)
        self.assertIn("udp_recv_buf > 0 && udp_recv_buf < (16 << 20)", patched)
        self.assertIn("rmem_max/wmem_max", patched)
        self.assertNotIn("sysctl -w", patched)

    def test_failed_and_short_read_dropped_before_authenticated_link(self):
        patched = v.patch(source_fixture())
        self.assertEqual(patched.count("m_socket->readDatagram("), 1)
        self.assertIn("bytes_read <= 0 || bytes_read != raw.size()", patched)
        self.assertLess(patched.index("bytes_read <= 0"), patched.index("continue;"))
        self.assertNotIn("m_socket->readDatagram(raw.data(), raw.size(), &sender, &senderPort);\n\n        if (raw.isEmpty())", patched)

    def test_idempotence_and_source_drift_fail_closed(self):
        original = source_fixture()
        rewritten = v.patch(original)
        with self.assertRaisesRegex(ValueError, "already applied"):
            v.patch(rewritten)
        for anchor in (v.BUFF_OLD, v.READ_OLD, "void LinkServer::OnReadyRead()",
                       "bool LinkServer::Start("):
            with self.subTest(anchor=anchor[:35]):
                with self.assertRaises(ValueError):
                    v.patch(original.replace(anchor, "unreviewed upstream drift"))

    def test_never_change_routes_or_send_protocol_and_no_player_telemetry(self):
        source = source_fixture()
        source += "\nvoid LinkServer::HandleLink() { Apply(m_link.Receive(from, datagram, now)); }\n"
        patched = v.patch(source)
        self.assertIn("Apply(m_link.Receive(from, datagram, now))", patched)
        for secret in ("online_id", "auth_ticket", "data().toHex()", "packet_payload",
                       "sender.toString()", "SHYT_ENABLE_TEST_LOCAL_MTLS"):
            self.assertNotIn(secret, v.BUFF_NEW + v.READ_NEW)
        self.assertNotIn("throw ", v.BUFF_NEW + v.READ_NEW)
        self.assertNotIn("return false;", v.BUFF_NEW + v.READ_NEW)


if __name__ == "__main__":
    unittest.main()
