#!/usr/bin/env python3
"""Enable explicit isolated remote Fornex *test* ports in Yharnam Together BLauncher.

No server-side schema or protocol changes; this only corrects the explicit
IPv4 endpoint/port selection for remote guest connections. Local host and all
ordinary upstream players keep 31314/31315/20443. Players must opt in by
creating user/seamless-hunt-network.json. Never silently forward credentials
or crash dumps to an alternate server. Uses source-anchor matching so future
Yharnam Together versions reject unsafe blind changes.
"""
from __future__ import annotations
import argparse
from pathlib import Path

COOP = "bbport/launcher/bbport_coop.py"
LAUNCHER = "bbport/launcher/bbport_launcher_win.py"
MARKER = "SHYT-V46-EXPLICIT-REMOTE-PORTS"
PORTS = ("udp_game_port", "webapi_tcp_port", "backend_tcp_port")
PROFILE_IMPL = r'''# SHYT-V46-EXPLICIT-REMOTE-PORTS
# This is only for players opting into a remote *staging* server.
# Neither Direct P2P nor global matchmaking is enabled by this configuration.
def shyt_remote_ports(install, host_ip):
    normal = {'udp_game_port': MATCHING_PORT, 'webapi_tcp_port': WEBAPI_PORT,
              'backend_tcp_port': BACKEND_PORT, 'custom': False}
    if install is None:
        return normal
    profile_file = Path(install) / 'user' / 'seamless-hunt-network.json'
    if not profile_file.exists():
        return normal
    if not profile_file.is_file():
        raise ValueError('Seamless Hunt server profile path is not a file')
    if not valid_ip(host_ip) or is_this_pc(host_ip):
        raise ValueError('Seamless Hunt custom ports are for remote IPv4 guests only')
    try:
        data = json.loads(profile_file.read_text(encoding='utf-8'))
    except (ValueError, OSError, UnicodeError) as exc:
        raise ValueError('Cannot read test-only Seamless Hunt network profile') from exc
    allowed = {'schema', 'opt_in', 'server_ipv4', 'udp_game_port',
               'webapi_tcp_port', 'backend_tcp_port'}
    if not isinstance(data, dict) or set(data) != allowed:
        raise ValueError('Invalid Seamless Hunt network profile keys')
    if type(data['schema']) is not int or data['schema'] != 1 or data['opt_in'] is not True:
        raise ValueError('Staging server connection requires explicit opt-in')
    if not isinstance(data['server_ipv4'], str) or data['server_ipv4'] != host_ip:
        raise ValueError('The staging profile IPv4 must match Host IP in the launcher')
    values = [data[k] for k in ('udp_game_port', 'webapi_tcp_port', 'backend_tcp_port')]
    if any(type(value) is not int or not 1024 <= value <= 65535 for value in values):
        raise ValueError('Staging server ports must be integer ports 1024..65535')
    if len(set(values)) != 3:
        raise ValueError('Staging UDP/WebAPI/backend ports must be distinct')
    return {'udp_game_port': values[0], 'webapi_tcp_port': values[1],
            'backend_tcp_port': values[2], 'custom': True}


'''

def once(source: str, before: str, after: str, context: str) -> str:
    n = source.count(before)
    if n != 1:
        raise ValueError(f"V46 pinned {context} anchor changed ({n} occurrences)")
    return source.replace(before, after, 1)


def transform_coop(source: str) -> str:
    if MARKER in source:
        raise ValueError("V46 remote endpoint ports already patched")
    if "SHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = 31313, 31315, 31314, 20443" not in source:
        raise ValueError("Yharnam Together port constants changed")
    source = once(source, "def host_overrides(host_ip):\n",
                  PROFILE_IMPL + "def host_overrides(host_ip, install=None):\n", "remote helper")
    source = once(source,
                  "    return json.dumps({GAME_SERVER: f'http://{host_ip}:{BACKEND_PORT}'}, indent=2) + '\\n'",
                  "    profile = shyt_remote_ports(install, host_ip)\n"
                  "    return json.dumps({GAME_SERVER: f'http://{host_ip}:{profile[\"backend_tcp_port\"]}'}, indent=2) + '\\n'",
                  "backend host override")
    source = once(source,
                  "    host = settings['host_ip']\n    env.update({",
                  "    host = settings['host_ip']\n"
                  "    profile = shyt_remote_ports(install, host)\n"
                  "    env.update({", "game startup environment")
    source = once(source,
                  "'BB_SHADNET_SERVER': f'{host}:{MATCHING_PORT}', 'BB_SHADNET_WEBAPI': f'http://{host}:{WEBAPI_PORT}',",
                  "'BB_SHADNET_SERVER': f'{host}:{profile[\"udp_game_port\"]}', "
                  "'BB_SHADNET_WEBAPI': f'http://{host}:{profile[\"webapi_tcp_port\"]}',",
                  "game UDP and WebAPI environment")
    source = once(source,
                  "def report_request(host_ip, path, data, player, secret):",
                  "def report_request(host_ip, path, data, player, secret, webapi_port=WEBAPI_PORT):",
                  "crash reporter function")
    source = once(source,
                  "f'http://{host_ip}:{WEBAPI_PORT}/bb/report/{Path(path).name}'",
                  "f'http://{host_ip}:{webapi_port}/bb/report/{Path(path).name}'",
                  "crash-report destination port")
    source = once(source,
                  "    log = Path(install) / 'user' / 'log'\n    sent = []\n    for path in reports_to_send(log):",
                  "    profile = shyt_remote_ports(install, settings['host_ip'])\n"
                  "    # Avoid sending account secrets/dumps to a test community realm.\n"
                  "    # This never disables upstream reporting for ordinary installations.\n"
                  "    if profile['custom']:\n"
                  "        return 0\n"
                  "    log = Path(install) / 'user' / 'log'\n"
                  "    sent = []\n"
                  "    for path in reports_to_send(log):",
                  "remote crash dump privacy")
    return source


def transform_launcher(source: str) -> str:
    if "SHYT-V46-REMOTE-LAUNCHER-PORTS" in source:
        raise ValueError("V46 launcher already patched")
    return once(source,
                "bbport_coop.host_overrides(settings['host_ip'])",
                "bbport_coop.host_overrides(settings['host_ip'], PORT_DIR)  # SHYT-V46-REMOTE-LAUNCHER-PORTS",
                "launcher custom game backend port")


def transform(src: dict[str, str]) -> dict[str, str]:
    if set(src) != {COOP, LAUNCHER}:
        raise ValueError("expected both original Yharnam Together launcher and coop source")
    return {COOP: transform_coop(src[COOP]),
            LAUNCHER: transform_launcher(src[LAUNCHER])}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("coop", type=Path)
    a.add_argument("launcher", type=Path)
    opts = a.parse_args()
    code = transform({COOP: opts.coop.read_text("utf-8"),
                      LAUNCHER: opts.launcher.read_text("utf-8")})
    opts.coop.write_text(code[COOP], "utf-8")
    opts.launcher.write_text(code[LAUNCHER], "utf-8")
    print("SHYT_V46_PINNED_REMOTE_FORNEX_ENDPOINTS_PATCHED")
