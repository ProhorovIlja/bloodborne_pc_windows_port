#!/usr/bin/env bash
# READ-ONLY Fornex inventory: never dump config/database content,
# environment variables, SSH keys, credentials or process arguments.
set -uo pipefail
umask 077
out="/tmp/SHYT-FORNEX-LIVE-$(date -u +%Y%m%dT%H%M%SZ).txt"
: > "$out" || exit 1
chmod 600 "$out"
section(){ printf '\n=== %s ===\n' "$1" >> "$out"; }
run(){ section "$1"; shift; timeout 15 "$@" >> "$out" 2>&1 || echo "[unavailable or timed out]" >> "$out"; }
section 'UTC and Linux version'
date -u >> "$out"; uname -a >> "$out"; grep -E '^(NAME|VERSION|PRETTY_NAME|ID)=' /etc/os-release >> "$out" 2>&1
run 'CPU' bash -c "lscpu | grep -E '^(Architecture|CPU\(s\)|Model name|Core\(s\) per socket|Thread\(s\) per core):'"
run 'MEMORY' free -h
run 'STORAGE' df -hT / /root /opt /srv /var/lib
run 'PRESSURE' bash -c 'cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io'
run 'LISTENING PORTS, NO CLIENT CONNECTIONS' bash -c 'ss -H -lntup | head -n 130'
run 'PROCESS NAMES, NO ARGUMENTS' bash -c "ps -eo pid,ppid,comm,etimes,%cpu,%mem | grep -Ei 'shadnet|bloodborne|bbsc|bbport|python|relay|nginx|caddy' | head -n 95 || true"
run 'RELEVANT SYSTEMD SERVICES' bash -c "systemctl list-units --all --no-pager --type=service | grep -Ei 'bloodborne|bbsc|shadnet|yharnam|shyt|seamless|relay|nginx|caddy' | head -n 90 || true"
section 'UNIT PROPERTIES, NO ENV OR EXECSTART'
while read -r unit; do
  [[ -n "$unit" ]] || continue
  echo "-- $unit" >> "$out"
  timeout 5 systemctl show "$unit" --no-pager -p FragmentPath -p ActiveState -p SubState -p User -p Group -p WorkingDirectory -p MainPID >> "$out" 2>&1 || true
done < <(systemctl list-unit-files --no-legend --no-pager --type=service 2>/dev/null | awk '{print $1}' | grep -Ei 'bloodborne|bbsc|shadnet|yharnam|shyt|seamless|relay' | head -n 40 || true)
run 'CONTAINERS (NO ENVIRONMENT)' bash -c 'command -v docker >/dev/null && docker ps -a --format "{{.Names}} {{.Image}} {{.Status}} {{.Ports}}" | head -n 60 || true'
run 'SERVER BINARY AND CONFIG PATHS ONLY' bash -c '
for dir in /root /opt /srv /usr/local/bin /etc/systemd/system /home; do
  [[ -d "$dir" ]] || continue
  timeout 12 find "$dir" -maxdepth 6 -type f \( -name shadnet -o -name "*bbsc*.service" -o -name "*shadnet*.service" -o -name "*yharnam*.service" -o -name "*shyt*.service" -o -name "bb_dummy_server.py" -o -name "*shadnet*.cfg" -o -name "PORTABLE-RECOVERY.py" \) -printf "%p | %s bytes\n" 2>/dev/null | head -n 150 || true
done'
run 'FIREWALL SUMMARY ONLY' bash -c 'command -v ufw >/dev/null && ufw status | head -n 80 || true; command -v nft >/dev/null && nft list tables | head -n 20 || true'
section 'COMPLETE'
echo 'Read-only inventory. No existing services/files changed. No DBs, savedata or secrets read.' >> "$out"
printf 'REPORT=%s\n' "$out"
printf 'SIZE=%s bytes\n' "$(wc -c < "$out")"
echo 'Upload only that report text file; never upload private keys, passwords or databases.'
