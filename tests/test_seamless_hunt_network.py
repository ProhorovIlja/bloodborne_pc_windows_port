"""Offline STUN protocol and route-diagnostic tests. Never contact the Internet."""
import paths  # noqa: F401
import ipaddress
import socket
import struct
import unittest
from unittest import mock

import seamless_hunt_network as network


def stun_answer(tid: bytes, addr="8.8.8.8", port=49000, *, xor=True) -> bytes:
    ip = ipaddress.ip_address(addr)
    key = struct.pack("!I", network.COOKIE) + tid
    bits = ip.packed
    if xor:
        bits = bytes(a ^ b for a, b in zip(bits, key))
    body = b"\x00" + (b"\x01" if ip.version == 4 else b"\x02")
    body += struct.pack("!H", port ^ (network.COOKIE >> 16) if xor else port)
    body += bits
    attr = struct.pack("!HH", network.XOR_MAPPED if xor else network.MAPPED, len(body)) + body
    return struct.pack("!HHI", network.BIND_SUCCESS, len(attr), network.COOKIE) + tid + attr


class StubSocket:
    def __init__(self, response, addr):
        self.response, self.addr = response, addr
        self.sent = []
        self.timeout = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendto(self, request, addr):
        self.sent.append((request, addr))
        return len(request)

    def recvfrom(self, _length):
        return self.response, self.addr


class StunTests(unittest.TestCase):
    def test_target_parsing(self):
        self.assertEqual(network.parse_stun_target("stun.l.google.com:19302"),
                         ("stun.l.google.com", 19302))
        self.assertEqual(network.parse_stun_target("localhost"), ("localhost", 3478))
        self.assertEqual(network.parse_stun_target("[2001:db8::1]:1000"),
                         ("2001:db8::1", 1000))
        self.assertIsNone(network.parse_stun_target("off"))
        self.assertIsNone(network.parse_stun_target(""))
        for bad in ("https://host", "host:0", "host:65536", "host:abc",
                    "host:1/secret", "secret@host", "2001:db8::1",
                    "host:1\r\nHeader: 2"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                network.parse_stun_target(bad)

    def test_valid_xor_address_ipv4_and_ipv6(self):
        tid = b"0123456789ab"
        self.assertEqual(network._mapped_address(stun_answer(tid), tid), ("8.8.8.8", 49000))
        self.assertEqual(network._mapped_address(
            stun_answer(tid, "2001:4860:4860::8888", 53001), tid),
            ("2001:4860:4860::8888", 53001))
        self.assertEqual(network._mapped_address(
            stun_answer(tid, "1.1.1.1", 19302, xor=False), tid),
            ("1.1.1.1", 19302))

    def test_rejects_wrong_session_and_malformed_packets(self):
        tid = b"0123456789ab"
        valid = stun_answer(tid)
        for packet in (b"", valid[:10], valid[:21], valid[:-1],
                       valid[:8] + b"BADTRANSACT!"[:12] + valid[20:],
                       b"\x01\x01\x00\x0c\x00\x00\x00\x00" + valid[8:]):
            with self.subTest(packet=packet[:8]):
                self.assertIsNone(network._mapped_address(packet, tid))

    @mock.patch.object(network.secrets, "token_bytes", return_value=b"0123456789ab")
    @mock.patch.object(network.socket, "getaddrinfo")
    @mock.patch.object(network.socket, "socket")
    def test_probe_exactly_one_binding_and_no_user_secret(self, sock, resolve, _):
        addr = ("203.0.113.55", 19302)
        conn = StubSocket(stun_answer(b"0123456789ab"), addr)
        sock.return_value = conn
        resolve.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 17, "", addr)]
        result = network.probe_udp_stun("stun.example:19302")
        self.assertEqual(result.state, "ok")
        self.assertIn("NAT traversal not yet verified", result.message)
        self.assertNotIn("8.8.8.8", result.message)
        self.assertEqual(len(conn.sent), 1)
        self.assertEqual(conn.sent[0][0], struct.pack("!HHI", 1, 0, network.COOKIE) + b"0123456789ab")
        self.assertEqual(conn.sent[0][1], addr)

    @mock.patch.object(network.socket, "getaddrinfo", side_effect=socket.gaierror())
    def test_dns_failure(self, _):
        result = network.probe_udp_stun("offline.invalid:3478")
        self.assertEqual(result.state, "warning")
        self.assertIn("DNS", result.message)

    @mock.patch.object(network.socket, "getaddrinfo")
    def test_disabled_does_not_touch_network(self, resolve):
        row = network.probe_udp_stun("off")
        self.assertEqual(row.state, "off")
        resolve.assert_not_called()

    @mock.patch.object(network.socket, "socket")
    def test_ipv6_route_check_sends_no_packets(self, sock):
        class IPv6Sock(StubSocket):
            def connect(self, remote):
                self.remote = remote
            def getsockname(self):
                return ("2001:4860::23", 13579, 0, 0)
        sock.return_value = IPv6Sock(None, None)
        row = network.probe_ipv6_route()
        self.assertEqual(row.state, "ok")
        self.assertEqual(sock.return_value.remote[0], network.IPV6_ROUTE_TARGET)
        self.assertEqual(sock.return_value.sent, [])


if __name__ == "__main__":
    unittest.main()
