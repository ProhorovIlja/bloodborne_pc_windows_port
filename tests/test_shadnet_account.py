"""Offline tests of published BBSC/shadNet account Login request and reply."""
import paths  # noqa: F401
import socket
import struct
import unittest
from unittest import mock

import shadnet_account as acct
from bbsc_shadnet_wire import HEADER_BYTES


def frame(kind, cmd, req_id, body):
    return struct.pack("<BHIQ", kind, cmd, 15 + len(body), req_id) + body


def server_greeting(version=1):
    return frame(3, 0, 0, struct.pack("<I", version))


def login_reply(err=0, user_id=567):
    if err:
        return frame(1, 0, 1, bytes([err]))
    # shadnet/LoginReply: string avatar_url = 1; uint64 user_id = 2;
    # repeated FriendEntry friends = 3; unknown fields must be skipped.
    pb = acct._string_field(1, "avatar") + bytes([0x10]) + acct._varint(user_id)
    pb += bytes([0x1a, 0x03, 0x0a, 0x01, 0x78])
    return frame(1, 0, 1, b"\x00" + struct.pack("<I", len(pb)) + pb)


class FakeSocket:
    def __init__(self, inbound: bytes):
        self.buf = inbound
        self.sent = []
        self.timeout = None
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def settimeout(self, value):
        self.timeout = value

    def recv(self, size):
        data = self.buf[:min(size, 3)]  # intentionally fragmented
        self.buf = self.buf[len(data):]
        return data

    def sendall(self, data):
        self.sent.append(data)


class LoginWireTests(unittest.TestCase):
    def test_protocol_login_request_exact_binary_layout(self):
        packet = acct.make_login_request("Hunter_123", "pw!")
        self.assertEqual(struct.unpack("<BHIQ", packet[:15]),
                         (0, 0, len(packet), 1))
        size = struct.unpack_from("<I", packet, 15)[0]
        pb = packet[19:]
        self.assertEqual(size, len(pb))
        self.assertIn(acct._string_field(1, "Hunter_123"), pb)
        self.assertIn(acct._string_field(2, "pw!"), pb)
        self.assertIn(acct._string_field(4, "CUSA03173"), pb)
        self.assertIn(acct._string_field(5, "Bloodborne"), pb)

    def test_successful_diagnostic_auth(self):
        sock = FakeSocket(server_greeting() + login_reply())
        with mock.patch.object(acct.socket, "create_connection", return_value=sock) as conn:
            got = acct.check_account("PLAY.SeamlessHunt.COM", "Hunter_123", "secret42")
        self.assertTrue(got.accepted)
        self.assertEqual(got.user_id, 567)
        self.assertTrue(sock.closed)
        self.assertEqual(len(sock.sent), 1)
        self.assertNotIn("secret42", repr(got))
        conn.assert_called_once_with(("play.seamlesshunt.com", 31313), timeout=4.0)

    def test_invalid_password_and_already_logged_in(self):
        for err in (6, 8):
            with self.subTest(err=err):
                sock = FakeSocket(server_greeting() + login_reply(err))
                with mock.patch.object(acct.socket, "create_connection", return_value=sock):
                    result = acct.check_account("127.0.0.1", "Hunter", "bad")
                self.assertFalse(result.accepted)
                self.assertEqual(result.error_code, err)
                self.assertIn("logged in" if err == 6 else "password", result.status)

    def test_rejects_greeting_version_mismatch(self):
        sock = FakeSocket(server_greeting(2) + login_reply())
        with mock.patch.object(acct.socket, "create_connection", return_value=sock):
            result = acct.check_account("127.0.0.1", "Hunter", "secret")
        self.assertFalse(result.accepted)
        self.assertEqual(sock.sent, [])

    def test_rejects_wrong_reply_request_id(self):
        sock = FakeSocket(server_greeting() + frame(1, 0, 99, b"\x00"))
        with mock.patch.object(acct.socket, "create_connection", return_value=sock):
            result = acct.check_account("127.0.0.1", "Hunter", "secret")
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "Cannot connect or the server closed the connection")

    def test_rejects_malformed_success_proto(self):
        sock = FakeSocket(server_greeting() + frame(1, 0, 1, b"\x00\x10\x00\x00\x00"))
        with mock.patch.object(acct.socket, "create_connection", return_value=sock):
            result = acct.check_account("127.0.0.1", "Hunter", "secret")
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "Unexpected shadNet response or protocol mismatch")

    def test_no_network_for_invalid_credentials_or_host(self):
        with mock.patch.object(acct.socket, "create_connection") as conn:
            for host, username, pw in (
                ("evil.test:31313", "ok", "pw"),
                ("127.0.0.1", "../Hunter", "pw"),
                ("127.0.0.1", "Hunter", ""),
                ("127.0.0.1", "Hunter", "x" * 1025),
            ):
                with self.assertRaises(ValueError):
                    acct.check_account(host, username, pw)
            conn.assert_not_called()

    def test_timeout_is_safe_without_exception_details(self):
        with mock.patch.object(acct.socket, "create_connection", side_effect=socket.timeout):
            result = acct.check_account("127.0.0.1", "Hunter", "pw")
        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "Server timed out")


if __name__ == "__main__":
    unittest.main()
