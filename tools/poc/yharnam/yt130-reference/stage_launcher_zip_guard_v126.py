#!/usr/bin/env python3
"""Guard Windows BLauncher self-update against invalid/oversized ZIP archives.

The original official YT 1.3.0 launcher downloads and immediately extracts
a release ZIP, then executes any recursively discovered BLauncher.exe.
This stages on TOP of source-reviewed integrated launcher PR32 and preserves
TLS truststore validation, UTF8 diagnostics, atomic settings and actual game.
No release/update/real network is executed by this staging utility.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE = "bbport/launcher/bbport_launcher_win.py"
ORIGINAL_BLOB = "b54974c649610bef59e53a61ae294edc2d386cda"
LIMIT = 1024**3
HELPER_ANCHOR = "TAG_PREFIX = 'windows-v'\n\n"
HELPER = """MAX_BBPORT_UPDATE_DOWNLOAD = 1024 ** 3  # 1 GiB compressed download ceiling
MAX_BBPORT_UPDATE_EXPANDED = 3 * 1024 ** 3  # 3 GiB total decoded payload
MAX_BBPORT_UPDATE_ENTRIES = 18000


def validate_bbport_update_zip(package):
    \\"\\"\\"Validate one official portable update before extraction or executing it.

    No error path ever executes a file from the downloaded archive. Reject
    ambiguous Windows path aliases, symlinks, encrypted/overlarge members,
    damaged CRC, foreign archive layouts and missing native game binaries.
    This does not replace release signing or TLS certificate verification.
    \\"\\"\\"
    import stat
    from pathlib import PurePosixPath
    infos = package.infolist()
    if not infos or len(infos) > MAX_BBPORT_UPDATE_ENTRIES:
        raise ValueError('Invalid Windows update: empty/excessive archive file list')
    seen = set()
    total = 0
    required = {'bbport-windows/BLauncher.exe',
                'bbport-windows/Bloodborne.exe',
                'bbport-windows/bin/bb-probe.exe',
                'bbport-windows/bin/bb-gpu-capabilities.exe'}
    names = set()
    devices = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
               *(f'LPT{i}' for i in range(1, 10))}
    for item in infos:
        name = item.filename
        parts = PurePosixPath(name).parts
        segments = name.rstrip('/').split('/')
        if (not name.startswith('bbport-windows/') or not name.isascii()
                or name.startswith('/') or '\\\\' in name or ':' in name or '\\x00' in name
                or any(not s or s in ('.', '..') or s[-1:] in (' ', '.') for s in segments)
                or '..' in parts or any(s.split('.')[0].upper() in devices for s in segments)):
            raise ValueError('Invalid Windows update: unsafe or foreign archive path')
        canon = name.rstrip('/').casefold()
        if canon in seen:
            raise ValueError('Invalid Windows update: duplicate Windows filename')
        seen.add(canon)
        if stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK:
            raise ValueError('Invalid Windows update: symbolic link')
        if item.flag_bits & 1:
            raise ValueError('Invalid Windows update: encrypted file')
        if item.is_dir():
            continue
        names.add(name)
        total += item.file_size
        if item.file_size > MAX_BBPORT_UPDATE_DOWNLOAD or total > MAX_BBPORT_UPDATE_EXPANDED:
            raise ValueError('Invalid Windows update: expanded size limit')
        if item.compress_size and item.file_size > item.compress_size * 1000:
            raise ValueError('Invalid Windows update: excessive compression ratio')
    if not required.issubset(names):
        raise ValueError('Invalid Windows update: missing native executable')
    if package.testzip() is not None:
        raise ValueError('Invalid Windows update: damaged ZIP CRC')
    return True


"""
DOWNLOAD_ANCHOR = "total, done, shown = int(response.headers.get('Content-Length') or 0), 0, -1"
DOWNLOAD_REPLACE = """total, done, shown = int(response.headers.get('Content-Length') or 0), 0, -1
                    if total > MAX_BBPORT_UPDATE_DOWNLOAD:
                        raise ValueError('Windows update download exceeds 1 GiB')"""
CHUNK_ANCHOR = "                        done += len(chunk)\n"
CHUNK_REPLACE = """                        done += len(chunk)
                        if done > MAX_BBPORT_UPDATE_DOWNLOAD:
                            raise ValueError('Windows update download exceeds 1 GiB')
"""
EXTRACT_ANCHOR = """                with zipfile.ZipFile(archive) as package:
                    package.extractall(UPDATE_DIR / 'new')"""
EXTRACT_REPLACE = """                with zipfile.ZipFile(archive) as package:
                    validate_bbport_update_zip(package)
                    package.extractall(UPDATE_DIR / 'new')"""
FIND_ANCHOR = """                new = next((p.parent for p in (UPDATE_DIR / 'new').rglob('BLauncher.exe')), None)
                if not new:
                    raise OSError('BLauncher.exe is missing from the download')"""
FIND_REPLACE = """                new = UPDATE_DIR / 'new' / 'bbport-windows'
                if not (new / 'BLauncher.exe').is_file():
                    raise OSError('Official root BLauncher.exe is missing from the download')"""
EXCEPTION_ANCHOR = "            except (OSError, zipfile.BadZipFile) as failure:"
EXCEPTION_REPLACE = "            except (OSError, zipfile.BadZipFile, ValueError) as failure:"
REPLACEMENTS = (
    (HELPER_ANCHOR, HELPER_ANCHOR + HELPER),
    (DOWNLOAD_ANCHOR, DOWNLOAD_REPLACE),
    (CHUNK_ANCHOR, CHUNK_REPLACE),
    (EXTRACT_ANCHOR, EXTRACT_REPLACE),
    (FIND_ANCHOR, FIND_REPLACE),
    (EXCEPTION_ANCHOR, EXCEPTION_REPLACE),
)


def rewrite(source: str) -> str:
    if "atomic_utf8_write" not in source or "record_startup_failure" not in source:
        raise ValueError("Expected the already-reviewed integrated PR32 launcher first")
    if "validate_bbport_update_zip(package)" in source:
        raise ValueError("Already installed V126 update guard")
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError("Original pinned Windows updater source changed: " + repr(before[:65]))
        source = source.replace(before, after, 1)
    return source


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong pinned original YT1.3 checkout")
    if git(root, "rev-parse", "HEAD:" + FILE) != ORIGINAL_BLOB:
        raise ValueError("Original Windows launcher blob drift")
    file = root / FILE
    file.write_bytes(rewrite(file.read_text(encoding="utf-8")).encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V126_INTEGRATED_WINDOWS_UPDATE_ZIP_FAIL_CLOSED_GUARD_STAGED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_source_integrated_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_source_integrated_yt130_checkout)
