#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V7: assemble YT Windows GUI with a TRUSTED, exact-tag BBHost release.

Network downloads occur in the isolated CI workflow, never from this
script. BBHost v0.2.24 release SHA256SUMS MUST verify with upstream's
pinned Ed25519 public release key (src/host/updater.cpp at exact tag).
Archive hash MUST be signed. All ZIP paths and sizes are checked before
extracting; user saves, accounts, games, existing runtime and settings
are never overwritten. No proof of YT seamless gameplay is implied.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import zipfile

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

UPSTREAM_TAG = "v0.2.24"
ARCHIVE_NAME = "bbhost-win-v0.2.24.zip"
# Upstream's Ed25519 public release key, NOT a private signing key.
RELEASE_PUBLIC_KEY = bytes.fromhex(
    "ce83684ee94ec4b9c91cf6247a23d08f"
    "501cdd7a19733c8348ca3ed6aea7ad62"
)
MAX_MANIFEST = 65536
MAX_ARCHIVE = 80000000
MAX_MEMBERS = 6000
MAX_SINGLE_FILE = 200000000
MAX_TOTAL_UNCOMPRESSED = 600000000
SHA_LINE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+\*?([A-Za-z0-9._+-]+)$")


class ReleaseRejected(ValueError):
    pass


def verified_zip_v7(
    archive: Path, manifest: Path, signature: Path,
    public_key: bytes = RELEASE_PUBLIC_KEY
) -> zipfile.ZipFile:
    if any(x.is_symlink() or not x.is_file() for x in (archive,manifest,signature)):
        raise ReleaseRejected("Missing or linked signed upstream release input")
    if not (1000 < archive.stat().st_size <= MAX_ARCHIVE):
        raise ReleaseRejected("Invalid upstream runtime archive size")
    if not (1 <= manifest.stat().st_size <= MAX_MANIFEST) or signature.stat().st_size != 64:
        raise ReleaseRejected("Invalid Ed25519 signed manifest metadata")
    signed = manifest.read_bytes()
    try:
        VerifyKey(public_key).verify(signed,signature.read_bytes())
    except (ValueError,BadSignatureError) as error:
        raise ReleaseRejected("BBHost upstream release signature mismatch") from error
    expected = None
    for line in signed.decode("utf-8","strict").splitlines():
        found = SHA_LINE.fullmatch(line.strip())
        if not found:
            raise ReleaseRejected("Malformed upstream signed checksum line")
        if found[2] == ARCHIVE_NAME:
            if expected is not None:
                raise ReleaseRejected("Duplicate BBHost Windows archive entry")
            expected = found[1].lower()
    if expected is None:
        raise ReleaseRejected("Missing signed Windows BBHost archive")
    digest = hashlib.sha256()
    with archive.open("rb") as src:
        for chunk in iter(lambda:src.read(1024*1024),b""):
            digest.update(chunk)
    if digest.hexdigest()!=expected:
        raise ReleaseRejected("Windows BBHost ZIP does not match signed manifest")
    try:
        return zipfile.ZipFile(archive,"r")
    except (OSError,zipfile.BadZipFile) as error:
        raise ReleaseRejected("Signed BBHost archive is not a ZIP") from error


def safe_members_v7(archive: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo],PurePosixPath]:
    infos=archive.infolist()
    if not (1<=len(infos)<=MAX_MEMBERS):
        raise ReleaseRejected("Unsafe ZIP member count")
    total=0
    seen=set()
    executables=[]
    for info in infos:
        name=info.filename
        if "\x00" in name or "\\" in name or name.startswith("/") or ":" in name:
            raise ReleaseRejected("Unsafe ZIP path")
        pure=PurePosixPath(name)
        if not name or any(p in (".","..") for p in name.split("/")) or ".." in pure.parts:
            raise ReleaseRejected("Unsafe relative ZIP path")
        if info.file_size>MAX_SINGLE_FILE:
            raise ReleaseRejected("ZIP member too large")
        total+=info.file_size
        if total>MAX_TOTAL_UNCOMPRESSED:
            raise ReleaseRejected("Unsafe uncompressed ZIP size")
        mode=(info.external_attr>>16)&0xffff
        if stat.S_ISLNK(mode):
            raise ReleaseRejected("ZIP symlink rejected")
        key=pure.as_posix().casefold()
        if key in seen:
            raise ReleaseRejected("Windows casefold ZIP entry collision")
        seen.add(key)
        if pure.name.casefold()=="bbhost.exe" and not info.is_dir():
            executables.append(pure)
    if len(executables)!=1:
        raise ReleaseRejected("Expected exactly one Windows BBHost.exe")
    return infos,executables[0].parent


def install_verified_bbhost_v7(archive:Path,manifest:Path,signature:Path,launcher:Path,
                               public_key:bytes=RELEASE_PUBLIC_KEY)->None:
    if launcher.is_symlink() or not launcher.is_dir() or not (launcher/"BLauncher.exe").is_file():
        raise ReleaseRejected("Real frozen YT BLauncher.exe folder missing")
    target=launcher/"bbhost"
    if target.exists() or target.is_symlink():
        raise ReleaseRejected("Do not overwrite an installed BBHost engine")
    with verified_zip_v7(archive,manifest,signature,public_key) as pkg:
        infos,prefix=safe_members_v7(pkg)
        staging=launcher/".bbhost-new-v7"
        if staging.exists() or staging.is_symlink():
            raise ReleaseRejected("Unsafe stale BBHost installation staging directory")
        staging.mkdir()
        copied=0
        try:
            for item in infos:
                full=PurePosixPath(item.filename)
                # Preserve original ZIP's entire directory containing the
                # executable and all nested data/DLLs/plugins.
                if prefix!=PurePosixPath("."):
                    try: relative=full.relative_to(prefix)
                    except ValueError: continue
                else:
                    relative=full
                if not relative.parts or item.is_dir():
                    continue
                if any(part.endswith(" ") or part.endswith(".") or
                       part.upper() in {"CON","PRN","AUX","NUL","COM1","LPT1"}
                       for part in relative.parts):
                    raise ReleaseRejected("Unsafe Windows ZIP member name")
                out=staging.joinpath(*relative.parts)
                out.parent.mkdir(parents=True,exist_ok=True)
                with pkg.open(item) as src,out.open("xb") as dest:
                    shutil.copyfileobj(src,dest,1024*1024)
                copied+=1
            game=staging/"bbhost.exe"
            if not game.is_file() or game.stat().st_size<65536:
                raise ReleaseRejected("BBHost.exe not found after signed extraction")
            with game.open("rb") as inp:
                if inp.read(2)!=b"MZ":
                    raise ReleaseRejected("Signed archive does not contain Windows PE")
            (staging/"SHYT-EXPERIMENTAL.txt").write_text(
                "Upstream BBHost "+UPSTREAM_TAG+" verified against its signed release manifest.\n"
                "Official upstream source: https://github.com/droogie/bbhost\n"
                "License: GPL-3.0 or later. The original Yharnam Together UI is "
                "a separate GPL-compatible frontend.\n"
                "THIS IS AN EXPERIMENTAL ENGINE SELECTOR. YHARNAM TOGETHER "
                "SEAMLESS MULTIPLAYER IS NOT INTEGRATED INTO BBHOST YET.\n"
                "This package contains NO retail Bloodborne game assets.\n",
                encoding="utf-8"
            )
            if copied<1:
                raise ReleaseRejected("Empty signed Windows BBHost package")
            staging.rename(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    print("SHYT_V7_SIGNED_BBHOST_OFFICIAL_WINDOWS_ENGINE_WITH_YT_LAUNCHER_STAGED_PASS")


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-archive",required=True,type=Path)
    p.add_argument("--sha256sums",required=True,type=Path)
    p.add_argument("--signature",required=True,type=Path)
    p.add_argument("--launcher-folder",required=True,type=Path)
    a=p.parse_args()
    try:
        install_verified_bbhost_v7(a.upstream_archive,a.sha256sums,a.signature,a.launcher_folder)
    except (OSError,ReleaseRejected,UnicodeDecodeError) as error:
        raise SystemExit("SHYT_V7_SIGNED_BBHOST_PACKAGING_REFUSED: "+
                         type(error).__name__) from None


if __name__=="__main__":
    main()
