#!/usr/bin/env python3
"""Stage isolated Yharnam Together server configuration without modifying existing services."""
import argparse
import ipaddress
import json
from pathlib import Path
import shutil
import stat
import subprocess

PIN = '77e350743a7cb4524cfcc1782fb6e3af64e25b15'
PORTS = {'tcp': 32313, 'udp': 32314, 'webapi': 32315, 'backend': 21443}
PROD = {31313, 31314, 31315, 20443, 3478}

def within(path, parent):
    return path == parent or parent in path.parents

def ensure_stage(stage, checkout, binary):
    stage, checkout = stage.resolve(), checkout.resolve()
    forbidden = [Path('/'), Path('/opt/bbsc'), Path('/etc'), Path('/var/lib'), Path('/root')]
    if any(stage == p for p in forbidden) or within(stage, checkout) or within(checkout, stage):
        raise ValueError('Stage must be a dedicated directory separate from production and the source checkout')
    if stage.exists() and any(stage.iterdir()):
        raise ValueError('Stage is not empty; refusing to overwrite existing files')
    if binary is not None and not binary.resolve(strict=True).is_file():
        raise ValueError('Missing server binary')
    if not (checkout / 'server' / 'coop' / 'team_lobby.h').is_file():
        raise ValueError('Not a Yharnam Together source checkout')
    result = subprocess.run(['git', '-C', str(checkout), 'rev-parse', 'HEAD'],
                            check=True, capture_output=True, text=True)
    actual = result.stdout.strip()
    if actual != PIN:
        raise ValueError(f'Source revision {actual} does not match pinned {PIN}')
    return stage, actual

def stage_server(checkout, stage, listen, advertise, binary=None):
    checkout, stage = Path(checkout), Path(stage)
    binary = Path(binary) if binary else None
    stage, sha = ensure_stage(stage, checkout, binary)
    ipaddress.IPv4Address(listen)
    if advertise:
        addr = ipaddress.IPv4Address(advertise)
        if addr.is_unspecified or addr.is_loopback:
            raise ValueError('Advertised address must be reachable from clients')
    if set(PORTS.values()) & PROD:
        raise ValueError('PoC ports collide with production ports')
    state = stage / 'state'
    state.mkdir(parents=True, exist_ok=False)
    (state / 'db').mkdir()
    (state / 'bloodborne_worlds').mkdir()
    (stage / 'bin').mkdir()
    if binary:
        target = stage / 'bin' / 'shadnet'
        shutil.copy2(binary, target)
        target.chmod(target.stat().st_mode | stat.S_IXUSR)
    for name in ('worlds.cfg', 'scoreboards.cfg'):
        shutil.copy2(checkout / 'server' / name, state / name)
    cfg = f'''[General]
Host={listen}
UnsecuredPort={PORTS["tcp"]}
MatchingUdpPort={PORTS["udp"]}
WebApiPort={PORTS["webapi"]}
BackendPort={PORTS["backend"]}
BackendAddress={advertise}
BloodborneSeamlessCoop=true
BloodborneBackend=true
Matching2Enabled=true
MakeAccountsAtSignIn=true
TcpLocalOnly=true
StatsEnabled=false
BloodborneWorldPath=bloodborne_worlds
BackendFolder={(checkout / 'backend').resolve()}
EmailValidated=false
AdminsList=
RegistrationSecretKey=
'''
    (state / 'shadnet.cfg').write_text(cfg, encoding='utf-8')
    runner = '''#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export SHADNET_HOME="$HERE/state"
if [[ ! -x "$HERE/bin/shadnet" ]]; then
  echo "Server binary missing. Build upstream Linux shadnet first." >&2
  exit 2
fi
if [[ "$(id -u)" -eq 0 ]]; then
  echo "Refusing to run as root." >&2
  exit 2
fi
cd "$SHADNET_HOME"
exec "$HERE/bin/shadnet"
'''
    output = stage / 'run-foreground.sh'
    output.write_text(runner, encoding='utf-8')
    output.chmod(0o755)
    manifest = {'source': 'lKaniel/bloodborne-server', 'revision': sha,
                'staging_only': True, 'listen': listen, 'advertise': advertise,
                'ports': PORTS, 'binary_staged': bool(binary),
                'production_untouched': True, 'live_server_tested': False}
    (stage / 'POC-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('STAGED', stage)
    print('Ports', PORTS)
    print('No production service or game files changed.')
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--advertise', default='')
    parser.add_argument('--binary', type=Path)
    args = parser.parse_args()
    try:
        stage_server(args.checkout, args.stage, args.bind, args.advertise, args.binary)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
