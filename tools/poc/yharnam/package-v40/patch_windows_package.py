#!/usr/bin/env python3
"""Fail-closed staging of native seamless co-op *event patcher* in bbport Windows ZIP.

No proprietary game event data is included. Each player generates patched
EMEVD files locally from their own Bloodborne 1.09 assets. This only fixes
package completeness; NPC summons and guest interactions remain game-test gates.
"""
from pathlib import Path
import argparse

MARKER = "# SH-YT-V40-COOP-EVENT-PATCHER"
ANCHOR = 'find "$dest" -name __pycache__ -prune -exec rm -r {} +'
STAGING = '''# SH-YT-V40-COOP-EVENT-PATCHER
# The prepared client MUST ship the pinned cooperative event script.
# The player supplies their own 1.09 event data; do not distribute EMEVD.
event_patcher=../tools/re/party_boss_events.py
if [[ ! -s "$event_patcher" ]]; then
    echo "Missing pinned co-op event script; refusing to package" >&2
    exit 1
fi
mkdir -p "$dest/tools"
cp "$event_patcher" "$dest/tools/party_boss_events.py"
test -s "$dest/tools/party_boss_events.py"
'''


def transform(source: str) -> str:
    if MARKER in source:
        raise ValueError("V40 event packager already applied")
    if source.count(ANCHOR) != 1:
        raise ValueError("pinned upstream package.sh changed: refusing unsafe edit")
    if "out/pyenv/Scripts/python.exe -I packaging/windows/make_zip.py" not in source:
        raise ValueError("native ZIP entrypoint is absent")
    if 'cp -r scripts patches "$dest/"' not in source:
        raise ValueError("native output staging layout changed")
    result = source.replace(ANCHOR, STAGING + ANCHOR)
    if result.count(MARKER) != 1:
        raise ValueError("failed to stage co-op event patcher")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_script", type=Path)
    args = ap.parse_args()
    text = args.package_script.read_text(encoding="utf-8")
    patched = transform(text)
    args.package_script.write_text(patched, encoding="utf-8")
    print("SH_YT_V40_COOP_EVENT_PACKAGER_APPLIED; game event assets not included")


if __name__ == "__main__":
    main()
