"""Yharnam Together BLauncher V46 guest-only Fornex endpoint tests."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("shyt_v46_endpoints", HERE / "patch_remote_ports.py")
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)

COOP_FIXTURE = '''import json
from pathlib import Path
SHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = 31313, 31315, 31314, 20443
def host_overrides(host_ip):
    """user host overrides"""
    return json.dumps({GAME_SERVER: f'http://{host_ip}:{BACKEND_PORT}'}, indent=2) + '\\n'
def game_environment(env, settings, install, root):
    host = settings['host_ip']
    env.update({
        'BB_SHADNET_SERVER': f'{host}:{MATCHING_PORT}', 'BB_SHADNET_WEBAPI': f'http://{host}:{WEBAPI_PORT}',
        'BB_SHADNET_NPID': settings['account'], 'BB_SHADNET_PASSWORD': settings['password'],
    })
    return env
def report_request(host_ip, path, data, player, secret):
    return urllib.request.Request(f'http://{host_ip}:{WEBAPI_PORT}/bb/report/{Path(path).name}', data=data,
                                  method='POST', headers={'X-Player': player})
def send_reports(install, settings, timeout=30):
    log = Path(install) / 'user' / 'log'
    sent = []
    for path in reports_to_send(log):
        request = report_request(settings['host_ip'], path, path.read_bytes(), settings['account'],
                                 settings['password'])
    return len(sent)
'''
LAUNCHER_FIXTURE = "result = bbport_coop.host_overrides(settings['host_ip'])\n"


class EndpointProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.install = Path(self.temp.name)
        self.config_path = self.install / "user" / "seamless-hunt-network.json"
        ns = {"json": json, "Path": Path, "MATCHING_PORT": 31314,
              "WEBAPI_PORT": 31315, "BACKEND_PORT": 20443,
              "valid_ip": lambda value: value == "198.51.100.24",
              "is_this_pc": lambda value: value == "198.51.100.1"}
        exec(p.PROFILE_IMPL, ns)
        self.profile = ns["shyt_remote_ports"]

    def write(self, value):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(value), "utf-8")

    def valid(self):
        return {"schema": 1, "opt_in": True, "server_ipv4": "198.51.100.24",
                "udp_game_port": 32314, "webapi_tcp_port": 32315,
                "backend_tcp_port": 21443}

    def test_upstream_ports_unchanged_without_explicit_profile(self):
        self.assertEqual(self.profile(self.install, "198.51.100.1"),
                         {"udp_game_port": 31314, "webapi_tcp_port": 31315,
                          "backend_tcp_port": 20443, "custom": False})
        self.assertFalse(self.profile(self.install, "198.51.100.24")["custom"])
        self.assertFalse(self.profile(None, "198.51.100.24")["custom"])

    def test_isolated_fornex_profile_selects_all_three_real_ports(self):
        self.write(self.valid())
        result = self.profile(self.install, "198.51.100.24")
        self.assertEqual(result["udp_game_port"], 32314)
        self.assertEqual(result["webapi_tcp_port"], 32315)
        self.assertEqual(result["backend_tcp_port"], 21443)
        self.assertTrue(result["custom"])

    def test_local_server_never_inherits_remote_staging_ports(self):
        self.write(self.valid())
        with self.assertRaisesRegex(ValueError, "remote IPv4 guests"):
            self.profile(self.install, "198.51.100.1")

    def test_mismatch_bad_ports_credentials_and_missing_consent_rejected(self):
        mutations = [
            {"opt_in": False}, {"opt_in": 1}, {"schema": 2},
            {"schema": True}, {"schema": 1.0}, {"schema": "1"}, {"schema": None},
            {"server_ipv4": "198.51.100.1"},
            {"udp_game_port": 32315}, {"udp_game_port": True},
            {"udp_game_port": 999}, {"backend_tcp_port": 65536},
            {"backend_tcp_port": "21443"}, {"password": "DO-NOT-STORE-CREDENTIALS"},
        ]
        for change in mutations:
            with self.subTest(change=change):
                candidate = self.valid()
                candidate.update(change)
                self.write(candidate)
                with self.assertRaises(ValueError):
                    self.profile(self.install, "198.51.100.24")

    def test_bad_json_is_a_failure_not_silent_rollback(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("{ garbage", "utf-8")
        with self.assertRaisesRegex(ValueError, "Cannot read"):
            self.profile(self.install, "198.51.100.24")

    def test_source_rewrites_python_coop_and_real_launcher_without_new_gui(self):
        result = p.transform({p.COOP: COOP_FIXTURE, p.LAUNCHER: LAUNCHER_FIXTURE})
        ast.parse(result[p.COOP])
        ast.parse(result[p.LAUNCHER])
        self.assertIn('profile["udp_game_port"]', result[p.COOP])
        self.assertIn('profile["webapi_tcp_port"]', result[p.COOP])
        self.assertIn('profile["backend_tcp_port"]', result[p.COOP])
        self.assertIn("if profile['custom']:", result[p.COOP])
        self.assertIn("bbport_coop.host_overrides(settings['host_ip'], PORT_DIR)", result[p.LAUNCHER])
        with self.assertRaisesRegex(ValueError, "already patched"):
            p.transform_coop(result[p.COOP])

    def test_launcher_port_patch_keeps_multiline_write_text_valid(self):
        # Real pinned Yharnam Together constructs write_text across lines;
        # its comma was previously swallowed by the injected inline comment.
        source = ("def update(settings):\n"
                  "    return target.write_text(bbport_coop.host_overrides(settings['host_ip']),\n"
                  "                             encoding='utf-8')\n")
        patched = p.transform_launcher(source)
        ast.parse(patched)
        self.assertIn("settings['host_ip'], PORT_DIR),", patched)
        self.assertEqual(patched.count("SHYT-V46-REMOTE-LAUNCHER-PORTS"), 1)
        with self.assertRaisesRegex(ValueError, "already patched"):
            p.transform_launcher(patched)

    def test_source_drift_or_missing_real_launcher_rejected(self):
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            p.transform_launcher("legacy_launcher.py")
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            p.transform_coop(COOP_FIXTURE.replace("env.update({", "env = dict(env)"))
        with self.assertRaisesRegex(ValueError, "expected both"):
            p.transform({p.COOP: COOP_FIXTURE})


if __name__ == "__main__":
    unittest.main()
