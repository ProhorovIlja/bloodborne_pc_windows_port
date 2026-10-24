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
# Preserve visible English author credits and original license notices.
# Credits are source-controlled in Seamless Hunt and copied by CI into the
# temporary Yharnam Together checkout, not into any retail game directory.
credits=../tools/release/kit/Seamless-Hunt-CREDITS.txt
if [[ ! -s "$credits" ]]; then
    echo "Missing downstream author and copyright notices" >&2
    exit 1
fi
cp "$credits" "$dest/CREDITS.txt"
# Store an EXAMPLE only. Real player endpoints stay in ignored user/ directory.
profile_example=../tools/release/kit/SeamlessHunt-network-profile.example.json
if [[ ! -s "$profile_example" ]]; then
    echo "Missing example for isolated remote co-op ports" >&2
    exit 1
fi
cp "$profile_example" "$dest/tools/SeamlessHunt-network-profile.example.json"
for notice in "$dest/LICENSE" "$dest/licenses/FireBurn-FSR-Vulkan-LICENSE.txt" "$dest/licenses/AMD-FidelityFX-SDK-LICENSE.txt" "$dest/licenses/Intel-XeSS-LICENSE.txt" "$dest/licenses/PkgTool-LICENSE.txt"; do
    if [[ ! -s "$notice" ]]; then
        echo "Missing upstream GPL or required redistributed third-party notice: $notice" >&2
        exit 1
    fi
done
test -s "$dest/CREDITS.txt"
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
