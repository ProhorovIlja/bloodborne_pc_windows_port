"""Seamless Hunt diagnostic contract: offline, no live server calls or credentials."""
import paths  # noqa: F401 -- adds scripts/ to the import path
import socket
import unittest
from unittest import mock

import seamless_hunt as sh


class FakeSocket:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class FakeResponse:
    status = 200

    def getheader(self, name, default=""):
        return "text/plain; charset=utf-8" if name == "Content-Type" else default


class FakeHTTP:
    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.request_args = None

    def request(self, method, path, headers):
        self.request_args = method, path, headers

    def getresponse(self):
        return FakeResponse()

    def close(self):
        pass


class Diagnostics(unittest.TestCase):
    def test_validate_host_accepts_only_host_not_url(self):
        self.assertEqual(sh.validate_host("PLAY.SeamlessHunt.COM"), sh.DEFAULT_HOST)
        self.assertEqual(sh.validate_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(sh.validate_host("[::1]"), "::1")
        for value in ("", " https://play.seamlesshunt.com", "http://evil",
                      "host:31313", "host/path", "host\r\nOther: yes",
                      "-bad.example", "bad..example", "bad label", "name@example"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sh.validate_host(value)

    @mock.patch.object(sh.socket, "create_connection")
    def test_tcp_probe_is_connect_only(self, connect):
        connect.return_value = FakeSocket()
        row = sh.probe_tcp("example.org", "shadNet", 31313)
        self.assertTrue(row.reachable)
        self.assertEqual(row.port, 31313)
        self.assertIsNotNone(row.latency_ms)
        connect.assert_called_once_with(("example.org", 31313), timeout=1.5)

    @mock.patch.object(sh.socket, "create_connection", side_effect=socket.timeout())
    def test_tcp_timeout_has_no_secret_error(self, _):
        result = sh.probe_tcp("example.org", "Web API", 31315)
        self.assertFalse(result.reachable)
        self.assertEqual(result.detail, "timeout")

    @mock.patch.object(sh.http.client, "HTTPConnection", side_effect=FakeHTTP)
    def test_game_server_uses_read_only_head(self, http):
        result = sh.probe_game_server("example.org")
        self.assertTrue(result.reachable)
        self.assertIn("/ss.info", result.detail)
        con = http.return_value
        # side_effect constructs instances rather than setting return_value:
        self.assertEqual(http.call_args.args, ("example.org", 20443))
        self.assertEqual(http.call_args.kwargs, {"timeout": 1.5})
        direct = FakeHTTP("example.org", 20443, 1.5)
        direct.request("HEAD", "/ss.info", {"User-Agent": "test"})
        self.assertEqual(direct.request_args[0:2], ("HEAD", "/ss.info"))

    def test_aggregate_probes_expected_ports(self):
        with mock.patch.object(sh, "probe_tcp") as tcp, \
             mock.patch.object(sh, "probe_shadnet") as wire, \
             mock.patch.object(sh, "probe_game_server") as game:
            tcp.side_effect = lambda host, name, port, timeout: sh.ServiceResult(name, port, True, 3, "reachable")
            wire.return_value = sh.ServiceResult("shadNet", 31313, True, 3, "handshake ok")
            game.return_value = sh.ServiceResult("GameServer", 20443, True, 5, "reachable")
            rows = sh.check_services("PLAY.SeamlessHunt.COM", timeout=99)
            self.assertEqual([r.port for r in rows], [31313, 31315, 20443])
            self.assertEqual(wire.call_args.args, (sh.DEFAULT_HOST, 31313, 5.0))
            self.assertEqual(tcp.call_args.args, (sh.DEFAULT_HOST, "Web API", 31315, 5.0))
            self.assertEqual(game.call_args.args, (sh.DEFAULT_HOST, 5.0))
            self.assertIn("shadNet 31313: OK", sh.format_results(rows))


if __name__ == "__main__":
    unittest.main()
