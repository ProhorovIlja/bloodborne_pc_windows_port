#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V441: bounded read-only audit of CLS YT v1.4.0's *actual* BBHost source.

No game files, binaries, production config, accounts or secrets are used.
A green result proves source provenance and an integrated hook loader exist,
NOT that online play or five-PC co-op works.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

PINNED_RELEASE = "v1.4.0"
SOURCE_SHA256 = "7c00d46f01b67ff1cf12cef346c245960b627141a9c1047d00e2ceadd167ca04"
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_ENTRIES = 30000
MAX_SOURCE = 300 * 1024
WANTED = ("src/yt/yt_host.cpp", "src/yt/yt_ui.cpp", "src/yt/yt_host.h")

class Refused(ValueError):
    pass

def verify(archive: Path, digest: str = SOURCE_SHA256) -> dict[str, object]:
    if archive.is_symlink() or not archive.is_file():
        raise Refused("archive must be an ordinary file")
    size = archive.stat().st_size
    if size < 256 or size > MAX_ARCHIVE:
        raise Refused("archive size outside source-only envelope")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise Refused("expected digest is not canonical sha256")
    sha = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    if sha != digest:
        raise Refused("source archive digest differs from pinned release")
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if not infos or len(infos) > MAX_ENTRIES:
            raise Refused("unsafe ZIP member count")
        members: dict[str, zipfile.ZipInfo] = {}
        for i in infos:
            name = i.filename.replace("\\", "/")
            parts = name.split("/")
            if name.startswith("/") or ".." in parts or not name.isascii():
                raise Refused("unsafe ZIP member name")
            if parts[-1].lower() == "eboot.bin" or parts[-1].lower().endswith(".pkg"):
                raise Refused("game binary must never be in source release")
            if i.is_dir():
                continue
            if name in members:
                raise Refused("duplicate ZIP member path")
            members[name] = i
        sources: dict[str, str] = {}
        for wanted in WANTED:
            found = [(n, m) for n, m in members.items()
                     if n == wanted or n.endswith("/" + wanted)]
            if len(found) != 1:
                raise Refused("missing or ambiguous BBHost-YT source: " + wanted)
            n, i = found[0]
            if i.file_size > MAX_SOURCE or i.file_size == 0:
                raise Refused("BBHost-YT source size out of bounds")
            try:
                sources[wanted] = z.read(i).decode("utf-8")
            except (UnicodeError, RuntimeError, EOFError) as exc:
                raise Refused("BBHost-YT source unreadable") from exc

    host = sources[WANTED[0]]
    ui = sources[WANTED[1]]
    required = {
        "yt_game_install": "bbcoop_install(" in host,
        "yt_np_imports": "bbnet_register(" in host,
        "yt_entrypoint": "yt_host_install(" in host,
        "yt_game_menu": "bbhost_yt_game_menu(" in (host + ui),
    }
    if not all(required.values()):
        raise Refused("released BBHost engine/NetSync integration unexpectedly absent")
    # Observations only: these require security / lifecycle review,
    # never silently authorize P2P or memory writes.
    observations = {
        "guarded_memory_query": "runtime_memory_protection(" in host,
        "memory_generation": "runtime_memory_generation(" in host,
        "saves_redirect": 'mklink /J' in host,
        "uses_rwx_hook_arena": "PAGE_EXECUTE_READWRITE" in host,
        "dedicated_bbhost_settings": "BBHOST_CONFIG_DIR" in host,
        "ui_len": len(ui),
    }
    return {
        "release": PINNED_RELEASE,
        "source_sha256": sha,
        "archive_bytes": size,
        "source_files_checked": len(WANTED),
        "required": required,
        "observations": observations,
        "proof_only": "source-provenance-and-hook-loader-not-playability"
    }

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--expected-sha256", default=SOURCE_SHA256)
    a = p.parse_args()
    try:
        result = verify(a.archive, a.expected_sha256)
    except (Refused, OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as e:
        raise SystemExit("V441_CLS_RELEASE_SOURCE_REFUSED: " + type(e).__name__) from None
    print(json.dumps(result, sort_keys=True))
    print("SHYT_V441_CLS_140_BBHOST_ACTUAL_INTEGRATION_SOURCE_PIN_PASS")

if __name__ == "__main__":
    main()
