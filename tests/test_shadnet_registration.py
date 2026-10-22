"""Offline private-server BBSC account creation contract tests."""
import paths  # noqa: F401
import struct
import unittest
from unittest import mock

import shadnet_account as acct
from test_shadnet_account import FakeSocket, frame, server_greeting


def create_reply(err):
    return frame(1, 2, 1, bytes([err]))


class RegistrationTests(unittest.TestCase):
    def test_create_packet_is_exact_bbsc_proto_schema(self):
        packet = acct.make_registration_request(
            "Hunter", "hunterpw", "hunter@example.org", "secretkey")
        self.assertEqual(struct.unpack("<BHIQ", packet[:15]), (0, 2, len(packet), 1))
        length = struct.unpack_from("<I", packet, 15)[0]
        pb = packet[19:]
        self.assertEqual(length, len(pb))
        self.assertIn(acct._string_field(1, "Hunter"), pb)
        self.assertIn(acct._string_field(2, "hunterpw"), pb)
        self.assertIn(acct._string_field(4, "hunter@example.org"), pb)
        self.assertIn(acct._string_field(5, "secretkey"), pb)

    def test_created_on_private_shadnet_server(self):
        sock = FakeSocket(server_greeting() + create_reply(0))
        with mock.patch.object(acct.socket, "create_connection", return_value=sock):
            result = acct.register_on_private_server(
                "127.0.0.1", "Hunter", "hunterpw", "hunter@example.org", "secretkey")
        self.assertTrue(result.accepted)
        self.assertEqual(result.error_code, 0)
        self.assertTrue(sock.closed)
        self.assertEqual(len(sock.sent), 1)
        self.assertNotIn("hunterpw", repr(result))
        self.assertNotIn("secretkey", repr(result))

    def test_key_required_by_server(self):
        sock = FakeSocket(server_greeting() + create_reply(23))
        with mock.patch.object(acct.socket, "create_connection", return_value=sock):
            result = acct.register_on_private_server(
                "localhost", "Hunter", "hunterpw", "hunter@example.org", "")
        self.assertFalse(result.accepted)
        self.assertEqual(result.error_code, 23)
        self.assertIn("registration key", result.status)

    def test_existing_id_returns_mapped_error(self):
        sock = FakeSocket(server_greeting() + create_reply(11))
        with mock.patch.object(acct.socket, "create_connection", return_value=sock):
            result = acct.register_on_private_server(
                "127.0.0.1", "Hunter", "hunterpw", "hunter@example.org", "key")
        self.assertFalse(result.accepted)
        self.assertIn("already exists", result.status)

    def test_public_server_cannot_register_via_wire(self):
        with mock.patch.object(acct.socket, "create_connection") as network:
            result = acct.register_on_private_server(
                "play.seamlesshunt.com", "Hunter", "pw", "x@y.net", "key")
            self.assertFalse(result.accepted)
            self.assertIn("website", result.status)
            network.assert_not_called()

    def test_invalid_credentials_do_not_access_network(self):
        with mock.patch.object(acct.socket, "create_connection") as network:
            with self.assertRaises(ValueError):
                acct.register_on_private_server("127.0.0.1", "Hunter",
                                                "pw", "bad-mail", "key")
            with self.assertRaises(ValueError):
                acct.register_on_private_server("127.0.0.1", "Hunter",
                                                "pw", "ok@host.net", "X" * 257)
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
