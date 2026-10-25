#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Read-only; captures service identity and listeners but never reads credentials.
# Safe for live Fornex. Does not restart/stop services or contact remote hosts.
set -euo pipefail

service=bbsc-shadnet.service
config=/opt/bbsc/shadnet/shadnet.cfg
binary=/opt/bbsc/shadnet/shadnet
expected=8b4b29b3e56414aa60bb53baa28285242b9a482e0a11e8dfe732ddc553094633

echo "SEAMLESS_HUNT_V62_READONLY_INVENTORY"
echo "GAME_SERVER_SERVICE:"
systemctl show "$service" -p ActiveState -p SubState -p MainPID --no-pager
echo "GAME_SERVER_BINARIES:"
if [[ -f "$binary" ]]; then
  printf 'installed_sha256='
  sha256sum "$binary" | cut -d' ' -f1
else
  echo "installed_binary_missing"
fi
pid="$(systemctl show "$service" -p MainPID --value 2>/dev/null || true)"
if [[ "$pid" =~ ^[1-9][0-9]*$ && -r "/proc/$pid/exe" ]]; then
  printf 'running_sha256='
  sha256sum "/proc/$pid/exe" | cut -d' ' -f1
else
  echo "no_readable_running_binary"
fi
printf 'candidate_sha256_from_2026_10_25=%s\n' "$expected"

echo "NON_SECRET_CONFIG:"
if [[ -r "$config" ]]; then
  # Explicit allowlist only, no password/token/key fields or arbitrary file reads.
  awk -F= '
    $1 == "BloodborneBackend" ||
    $1 == "BackendPort" ||
    $1 == "BackendStore" ||
    $1 == "BackendFolder" ||
    $1 == "MakeAccountsAtSignIn" ||
    $1 == "TcpLocalOnly" ||
    $1 == "UnsecuredPort" ||
    $1 == "MatchingUdpPort" ||
    $1 == "WebApiPort" ||
    $1 == "StatsPort" ||
    $1 == "Host" { if ($1 != "BackendFolder" && $1 != "BackendStore") print $1 "=" $2;
      else print $1 "=<configured path withheld>"; }
  ' "$config"
else
  echo "config_not_readable"
fi

echo "LISTENER_OWNERSHIP:"
# ss -p typically needs root to show process names. Do not print command lines.
if command -v ss >/dev/null 2>&1; then
  ss -H -lntup | awk '
    {
      localaddr=$5;
      port=localaddr;
      sub(/^.*:/,"",port);
      if(port=="31313" || port=="31314" || port=="31315" ||
         port=="31320" || port=="20443") {
        protocol=$1;
        ownership="unknown";
        if(match($0,/users:\(\("[^"]+"/))
          ownership=substr($0,RSTART+8,RLENGTH-9);
        print "port=" port " proto=" protocol " process=" ownership
      }
    }
  ' | sort -u
else
  echo "ss_not_installed"
fi

echo "SAFETY:"
echo "No config changes, no database reads, no HTTP requests, no service restarts."
echo "Never upload /opt/bbsc/shadnet/db or any auth/private settings to GitHub."
