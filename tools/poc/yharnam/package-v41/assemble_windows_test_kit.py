#!/usr/bin/env python3
"""Assemble a test-only native Bloodborne + Qt shadnet Windows kit.

This is deliberately NOT a release publishing tool. It only combines two
independently tested development ZIPs from the SAME pinned Yharnam source and
puts a release-blocking notice in the result. It never ships retail game files.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile

ROOT = "bbport-windows/"
SERVER_FILES = {
    "server/shadnet.exe", "server/shadnet.cfg",
    "server/Qt6Core.dll", "server/Qt6Network.dll", "server/Qt6Sql.dll",
    "server/sqldrivers/qsqlite.dll", "backend/bb_dummy_server.py",
    "backend/ss_info_template.xml", "licenses/GPL-2.0-or-later.txt",
    "NOT-RELEASE-READY.txt",
}
PRIVATE_PARTS = {"user", "savedata", "secrets", "dvdroot_ps4", "sce_module",
                 "sce_sys", "game", "coop-game", "db", ".git"}
PRIVATE_NAMES = {"eboot.bin", "shadnet.db", "coop.json", "bbport.ini",
                 "param.sfo", "host_overrides.custom.json", ".env"}
PRIVATE_EXTS = {".pkg", ".dcx", ".emevd", ".sav", ".pfx", ".pem", ".key",
                ".prx", ".sprx", ".sfo", ".bdt", ".bhd"}
CAP_ENTRIES = 18000
CAP_TOTAL = 3 * 1024**3
BLOCK_SIZE = 1024 * 1024


class InvalidCandidate(ValueError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(BLOCK_SIZE), b""):
            h.update(block)
    return h.hexdigest()


def verify_digest(path: Path, check_path: Path | None) -> str:
    result = digest(path)
    if check_path is not None:
        if check_path.read_text("ascii").splitlines() != [
            f"{result}  {path.name}"
        ]:
            raise InvalidCandidate(f"invalid SHA256 for {path.name}")
    return result


def allowed(name: str) -> None:
    if (not name or not name.isascii() or "\\" in name or "\x00" in name
            or name.startswith("/") or ":" in name):
        raise InvalidCandidate("unsafe or ambiguous ZIP member")
    parts = PurePosixPath(name.rstrip("/")).parts
    if (not parts or any(part in {".", "..", ""} for part in name.rstrip("/").split("/"))
            or any(p.lower() in PRIVATE_PARTS for p in parts[:-1])):
        raise InvalidCandidate("unsafe directory or private game data")
    leaf = parts[-1].lower()
    if leaf in PRIVATE_NAMES or any(leaf.endswith(ext) for ext in PRIVATE_EXTS):
        raise InvalidCandidate("proprietary asset, save or private key in archive")


def scan(z: zipfile.ZipFile, prefix: str) -> dict[str, zipfile.ZipInfo]:
    found: dict[str, zipfile.ZipInfo] = {}
    size = 0
    items = z.infolist()
    if not items or len(items) > CAP_ENTRIES:
        raise InvalidCandidate("empty/oversized ZIP archive")
    for info in items:
        raw = info.orig_filename
        allowed(raw)
        if not raw.startswith(prefix):
            raise InvalidCandidate("ZIP file outside its declared root")
        if info.is_dir():
            continue
        if raw in found:
            raise InvalidCandidate("duplicate ZIP entry")
        if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
            raise InvalidCandidate("ZIP symbolic link not allowed")
        size += info.file_size
        if size > CAP_TOTAL:
            raise InvalidCandidate("ZIP extraction size exceeded")
        found[raw] = info
    if z.testzip() is not None:
        raise InvalidCandidate("corrupt ZIP member")
    return found


def assemble(game: Path, server: Path, target: Path,
             *, game_sha: Path | None = None,
             server_sha: Path | None = None) -> dict:
    # Import the same validated playable ZIP contract as the V40 Windows build.
    repo = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo / "diagnostics"))
    from check_windows_candidate import check as check_game

    check_game(game, sha_path=game_sha)
    src_game_sha = verify_digest(game, game_sha)
    src_server_sha = verify_digest(server, server_sha)
    with zipfile.ZipFile(game) as gz, zipfile.ZipFile(server) as sz:
        games = scan(gz, ROOT)
        servers = scan(sz, "")
        for required in SERVER_FILES:
            if required not in servers:
                raise InvalidCandidate("Windows server or Qt dependency missing: " + required)
        for expected in ("server/shadnet.exe", "server/Qt6Core.dll"):
            if servers[expected].file_size < 1024:
                raise InvalidCandidate("placeholder Windows native server")
        for source_path in servers:
            if (ROOT + source_path in games or
                    source_path.startswith("bbport-windows/")):
                raise InvalidCandidate("game/server file collision")
        total = sum(x.file_size for x in list(games.values()) + list(servers.values()))
        if total > CAP_TOTAL:
            raise InvalidCandidate("combined Windows candidate exceeds safety cap")
        if target.resolve() in {game.resolve(), server.resolve()}:
            raise InvalidCandidate("output archive would overwrite an input")
        notice = (
            "INTERNAL COOPERATIVE DEVELOPMENT CANDIDATE - NOT A PUBLIC RELEASE\n"
            "No client gameplay, NPC summoning, mixed build matchmaking or PS4 "
            "compatibility is certified by this package check.\n"
            "Contains no original Bloodborne game assets. Install from your own game.\n"
        )
        metadata = {
            "release_ready": False, "game_zip_sha256": src_game_sha,
            "server_zip_sha256": src_server_sha,
            "upstream_pinned_revision": "77e350743a7cb4524cfcc1782fb6e3af64e25b15",
            "server_abi": "Windows x86_64, Qt 6.8.3 MSVC 2022",
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        try:
            with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=6, allowZip64=True) as out:
                for source_zip, contents, strip_root in [
                    (gz, games, False), (sz, servers, True)
                ]:
                    for name, entry in sorted(contents.items()):
                        outname = ROOT + name if strip_root else name
                        with source_zip.open(entry) as read, out.open(outname, "w",
                                                                    force_zip64=True) as write:
                            shutil.copyfileobj(read, write, BLOCK_SIZE)
                out.writestr(ROOT + "NOT-FOR-PUBLIC-RELEASE.txt", notice)
                out.writestr(ROOT + "SHYT-INTERNAL-CANDIDATE-MANIFEST.json",
                             json.dumps(metadata, indent=2, sort_keys=True) + "\n")
            with zipfile.ZipFile(partial) as result:
                if result.testzip() is not None:
                    raise InvalidCandidate("assembled ZIP integrity failed")
            partial.replace(target)
        finally:
            if partial.exists():
                partial.unlink()
    return {**metadata, "sha256": digest(target), "size": target.stat().st_size}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--game", type=Path, required=True)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--game-sha", type=Path)
    p.add_argument("--server-sha", type=Path)
    args = p.parse_args()
    try:
        result = assemble(args.game, args.server, args.out,
                          game_sha=args.game_sha, server_sha=args.server_sha)
    except (OSError, InvalidCandidate, ValueError, zipfile.BadZipFile) as e:
        p.exit(2, "COUPLED_WINDOWS_CANDIDATE_REJECTED: " + str(e) + "\n")
    checksum = args.out.with_suffix(args.out.suffix + ".sha256")
    checksum.write_text(result["sha256"] + "  " + args.out.name + "\n", encoding="ascii")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("COUPLED_WINDOWS_ARCHIVE_READY_INTERNAL_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
