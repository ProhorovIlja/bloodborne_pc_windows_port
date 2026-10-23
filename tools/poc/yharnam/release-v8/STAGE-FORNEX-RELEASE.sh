#!/usr/bin/env bash
# Stage a MATCHED reviewed server release on Fornex without affecting current servers.
set -Eeuo pipefail
if [[ $# != 4 ]]; then
  echo 'Usage: STAGE-FORNEX-RELEASE.sh <version> <shadnet> <release.json> <server-sha256>' >&2; exit 2
fi
VERSION="$1"; BINARY="$2"; MANIFEST="$3"; EXPECTED="$4"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.-]+)?$ ]] || { echo 'invalid version'; exit 1; }
[[ "$EXPECTED" =~ ^[0-9a-f]{64}$ ]] || { echo 'bad checksum'; exit 1; }
[[ "$(id -u)" == 0 ]] || { echo 'root required to stage file ownership'; exit 1; }
id shytpoc &>/dev/null || { echo 'dedicated shytpoc user missing'; exit 1; }
[[ -f "$BINARY" && -f "$MANIFEST" ]] || { echo 'missing files'; exit 1; }
python3 - "$MANIFEST" "$VERSION" "$EXPECTED" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
expected={
 'schema':1, 'release_tag':'shyt-v'+sys.argv[2],
 'client_protocol':8, 'server_protocol':8, 'link_protocol':2,
 'server_host':'199.195.193.131','server_sha256':sys.argv[3],
 'release_ready':True, 'server_deployed':True
}
for key,value in expected.items():
    if data.get(key)!=value: raise SystemExit('REFUSED: release manifest '+key+' not valid')
PY
[[ "$(sha256sum "$BINARY" | cut -d' ' -f1)" == "$EXPECTED" ]] || { echo 'binary digest mismatch'; exit 1; }
TARGET="/srv/sh-yt-releases/$VERSION"
[[ ! -e "$TARGET" ]] || { echo 'existing release, refusing overwrite'; exit 1; }
install -d -m 0750 -o shytpoc -g shytpoc "$TARGET"
install -m 0750 -o shytpoc -g shytpoc "$BINARY" "$TARGET/shadnet"
install -m 0640 -o shytpoc -g shytpoc "$MANIFEST" "$TARGET/seamless-hunt-release.json"
echo "STAGED ONLY: $TARGET"
echo 'Existing Yharnam server, CLS and firewall unchanged.'
echo 'Do not activate until isolated server startup and game-client compatibility tests pass.'
