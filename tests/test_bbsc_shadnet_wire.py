"""Pure offline tests of shadNet protocol-v1 greeting (CLSAMG22/BBSC)."""
import paths  # noqa: F401
import socket
import struct
import unittest
from unittest import mock
import bbsc_shadnet_wire as wire
import seamless_hunt as sh


def server_info(version=1, kind=3, extra=b""):
    payload = struct.pack("<I", version) + extra
    return struct.pack("<BHIQ", kind, 0, wire.HEADER_BYTES + len(payload), 0) + payload


class FakeSocket:
    def __init__(self, data, chunk_size=3):
        self.data = data
        self.chunk_size = chunk_size
        self.sent = []
        self.timeout = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def settimeout(self, value):
        self.timeout = value

    def recv(self, count):
        piece = self.data[:min(count, self.chunk_size)]
        self.data = self.data[len(piece):]
        return piece

    def send(self, data):
        self.sent.append(data)
        raise AssertionError("diagnostic must never send credentials or traffic")


class ShadNetGreetingTests(unittest.TestCase):
    def test_good_protocol_and_fragmentation(self):
        frame = server_info()
        header, body = frame[:15], frame[15:]
        self.assertEqual(wire.parse_greeting(header, body).version, 1)
        sock = FakeSocket(frame, chunk_size=2)
        with mock.patch.object(sh.socket, "create_connection", return_value=sock) as connect:
            result = sh.probe_shadnet("example.org")
        self.assertTrue(result.reachable)
        self.assertIn("v1", result.detail)
        self.assertIn("gameplay not verified", result.detail)
        self.assertEqual(sock.sent, [])
        connect.assert_called_once_with(("example.org", 31313), timeout=1.5)

    def test_reject_malformed_greetings(self):
        frame = server_info()
        bad = [
            b"",
            frame[:14],
            server_info(kind=0),
            server_info(version=2),
            frame[:3] + struct.pack("<I", 0xfffffff0) + frame[7:],
            frame[:3] + struct.pack("<I", 1) + frame[7:],
            frame[:15] + frame[15:-1],
        ]
        for payload in bad:
            with self.subTest(payload=payload[:8]):
                with mock.patch.object(sh.socket, "create_connection",
                                       return_value=FakeSocket(payload)):
                    result = sh.probe_shadnet("example.org")
                self.assertFalse(result.reachable)

    def test_header_unpack_contract(self):
        header = server_info()[:15]
        self.assertEqual(wire.parse_header(header), (3, 0, 19, 0))
        self.assertEqual(len(header), 15)


if __name__ == "__main__":
    unittest.main()
