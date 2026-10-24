#!/usr/bin/env bash
# Does not install or start services. Builds pinned Yharnam Together shadNet into an isolated output path.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo 'Usage: bash build_linux.sh /path/to/bloodborne-server /path/to/empty-output' >&2
  exit 2
fi
src="$(realpath "$1")"
out="$(realpath -m "$2")"
expected='77e350743a7cb4524cfcc1782fb6e3af64e25b15'
actual="$(git -C "$src" rev-parse HEAD)"
if [[ "$actual" != "$expected" ]]; then
 echo "Source revision mismatch: $actual != $expected; do not combine incompatible client/server" >&2
 exit 2
fi
if [[ -e "$out" && -n "$(ls -A "$out")" ]]; then
 echo "Output exists and is not empty: $out" >&2; exit 2
fi
if [[ "$out" == "$src"* || "$out" == /opt/bbsc* || "$out" == /root || "$out" == / ]]; then
 echo 'Unsafe build output directory' >&2; exit 2
fi
mkdir -p "$out"
cmake_args=(-S "$src/server" -B "$out" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON)
if [[ -n "${QT_ROOT:-}" ]]; then cmake_args+=("-DCMAKE_PREFIX_PATH=$QT_ROOT"); fi
cmake "${cmake_args[@]}"
cmake --build "$out" --parallel 2 --target shadnet test_team_lobby test_server_link
ctest --test-dir "$out" -R '^(team_lobby|server_link)$' --output-on-failure
printf '\nBUILT: %s/shadnet\n' "$out"
printf 'Not installed, not started, not exposed on any port.\n'
