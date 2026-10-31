#!/usr/bin/env python3
"""V185: read-only Windows BBSC native package and nested-runtime integrity gate.

No execution, extraction, networking, game bytes, secrets or public manifest.
Never mistake PE/runtime integrity for game boot or online/NAT success.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import sys
import zipfile

REQUIRED_PE = ('Bloodborne.exe', 'BLauncher.exe', 'bin/bb-probe.exe',
               'server/shadnet.exe')
REQUIRED = (*REQUIRED_PE, 'VERSION.txt', 'run.py')
MAX_FILES = 20_000
MAX_TOTAL = 4 * 1024**3
MAX_ENTRY = 768 * 1024**2
MAX_CONSOLE = 16_384
MANIFEST_SCHEMA = 'SHYT-NATIVE-PORT-PACKAGE-V185'

class PackageError(Exception):
    pass


def safe_path(path: str) -> str:
    if not path or '\\' in path or '\x00' in path or path.startswith('/'):
        raise PackageError('unsafe package path')
    bits = path.split('/')
    if any(p in ('', '.', '..') for p in bits) or ':' in bits[0]:
        raise PackageError('unsafe package path')
    return path


def validate_names(mapping: dict[str, object]) -> None:
    if len(mapping) > MAX_FILES:
        raise PackageError('package entry count exceeds limit')
    folded = set()
    for path in mapping:
        safe_path(path)
        lower = path.casefold()
        if lower in folded:
            raise PackageError('duplicate/case-conflicting runtime path')
        folded.add(lower)
        parts = [x.casefold() for x in path.split('/')]
        if 'eboot.bin' in parts or 'dvdroot_ps4' in parts or 'sce_sys' in parts or any(
                re.fullmatch(r'cusa\d{5}', p) for p in parts):
            raise PackageError('retail game content detected: cannot distribute')
    for path in REQUIRED:
        if path not in mapping:
            raise PackageError('required native runtime component missing: ' + path)


def pe_amd64(data: bytes) -> bool:
    if len(data) < 0x100 or data[:2] != b'MZ':
        return False
    loc = struct.unpack_from('<I', data, 0x3c)[0]
    return loc >= 64 and loc + 6 <= len(data) and data[loc:loc+4] == b'PE\0\0' and \
        struct.unpack_from('<H', data, loc+4)[0] == 0x8664


def zip_entries(z: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    infos = [i for i in z.infolist() if not i.is_dir()]
    # Single folder inside the ZIP is conventional; a flat ZIP is also valid.
    names = [i.filename for i in infos]
    prefixes = {n[:-len('Bloodborne.exe')] for n in names if n.endswith('Bloodborne.exe')}
    if len(prefixes) != 1:
        raise PackageError('ambiguous native package root')
    prefix, = prefixes
    result: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        if not info.filename.startswith(prefix):
            raise PackageError('file outside native package root')
        name = info.filename[len(prefix):]
        safe_path(name)
        kind = (info.external_attr >> 16) & 0o170000
        if kind == stat.S_IFLNK or info.flag_bits & 1:
            raise PackageError('symlink/encrypted runtime entry unsupported')
        if info.file_size > MAX_ENTRY:
            raise PackageError('runtime file exceeds per-entry budget')
        # Never unzip suspiciously compressed input into memory or on disk.
        if info.file_size > 2**20 and info.file_size > 1000 * max(1, info.compress_size):
            raise PackageError('excessive compression ratio')
        if name in result:
            raise PackageError('duplicate runtime path')
        result[name] = info
    return result


def dir_entries(root: Path) -> dict[str, Path]:
    if not root.is_dir() or root.is_symlink():
        raise PackageError('package directory not available')
    result: dict[str, Path] = {}
    for here, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            if (Path(here) / name).is_symlink():
                raise PackageError('symlink inside package')
        for name in files:
            p = Path(here) / name
            if p.is_symlink() or not p.is_file():
                raise PackageError('nonregular package file')
            rel = p.relative_to(root).as_posix()
            result[rel] = p
            if len(result) > MAX_FILES:
                raise PackageError('package entry count exceeds limit')
    return result


def read_and_hash(stream, expected_size: int) -> tuple[str, bytes]:
    h = hashlib.sha256()
    head = bytearray()
    size = 0
    while chunk := stream.read(256*1024):
        size += len(chunk)
        if size > MAX_ENTRY or size > expected_size:
            raise PackageError('runtime entry size changed during read')
        h.update(chunk)
        if len(head) < 8192:
            head.extend(chunk[:8192 - len(head)])
    if size != expected_size:
        raise PackageError('runtime entry size mismatch')
    return h.hexdigest(), bytes(head)


def inspect(package: Path) -> dict:
    is_zip = package.is_file() and package.suffix.lower() == '.zip'
    if is_zip:
        z = zipfile.ZipFile(package)
        members = zip_entries(z)
        def size_of(name): return members[name].file_size
        def open_file(name): return z.open(members[name])
    else:
        z = None
        members = dir_entries(package)
        def size_of(name): return members[name].stat().st_size
        def open_file(name): return members[name].open('rb')
    try:
        validate_names(members)
        aggregate = hashlib.sha256()
        hashes: dict[str, dict] = {}
        total = 0
        version = ''
        nested = 0
        for name in sorted(members):
            sz = size_of(name)
            total += sz
            if sz > MAX_ENTRY or total > MAX_TOTAL:
                raise PackageError('uncompressed runtime exceeds size budget')
            with open_file(name) as f:
                digest, header = read_and_hash(f, sz)
            if name in REQUIRED_PE and not pe_amd64(header):
                raise PackageError('required executable is not Windows x86-64 PE: ' + name)
            if name == 'VERSION.txt':
                if sz > 4096:
                    raise PackageError('version metadata too long')
                version = header.decode('utf-8', errors='strict').strip()
                if 'Bloodborne' not in version or 'Windows' not in version:
                    raise PackageError('unrecognized native Windows release metadata')
            if name.startswith('bin/') and name.count('/') > 1:
                nested += 1
            hashes[name] = {'size': sz, 'sha256': digest}
            aggregate.update(name.encode('utf-8') + b'\0' + str(sz).encode('ascii') + b'\0' + digest.encode('ascii') + b'\n')
        return {
            'schema': MANIFEST_SCHEMA,
            'summary': {'ok': True, 'pe_amd64_verified': len(REQUIRED_PE),
                        'file_count': len(members), 'nested_bin_count': nested,
                        'bytes_hashed': total, 'runtime_tree_sha256': aggregate.hexdigest(),
                        'gameplay_boot_tested': False, 'p2p_nat_tested': False,
                        'two_player_session_tested': False},
            'files': hashes,
        }
    finally:
        if z:
            z.close()


def inside_dir(root: Path, out: Path) -> bool:
    return root.is_dir() and out.resolve().is_relative_to(root.resolve())


def read_game_sfo(path: Path) -> dict[str, str]:
    """Offline read-only PSF metadata; never uploads game contents.

    The supported YT1.3 native game patch sites target Bloodborne 1.09
    CUSA03173. TITLE_ID alone is not a verification of the eboot's actual
    patch sites, and this is NOT a boot, decrypt or game-asset test.
    """
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 64 * 1024:
        raise PackageError('game param.sfo must be a small regular local file')
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b'\x00PSF':
        raise PackageError('invalid PSF game metadata')
    _magic, version, key_off, data_off, count = struct.unpack_from('<4sIIII', data)
    if version not in (0x101, 0x102) or count > 128 or 20 + 16 * count > len(data) or \
            key_off > len(data) or data_off > len(data):
        raise PackageError('invalid PSF offsets')
    values: dict[str, str] = {}
    for i in range(count):
        ko, fmt, sz, cap, dat = struct.unpack_from('<HHIII', data, 20 + 16 * i)
        if sz > cap or sz > 4096 or key_off + ko >= len(data) or \
                data_off + dat + sz > len(data):
            raise PackageError('invalid PSF table entry')
        end = data.find(b'\x00', key_off + ko, data_off)
        if end < 0:
            raise PackageError('invalid PSF key')
        name = data[key_off + ko:end].decode('ascii', 'strict')
        if name in ('APP_VER', 'TITLE_ID'):
            if name in values or fmt not in (0x204, 0x4):
                raise PackageError('invalid/duplicate PSF game version field')
            values[name] = data[data_off + dat:data_off + dat + sz].split(b'\x00', 1)[0].decode('ascii', 'strict')
    if values.get('TITLE_ID') != 'CUSA03173' or values.get('APP_VER') != '01.09':
        raise PackageError('game edition/update incompatible with pinned YT1.3 1.09 hooks')
    return values


def read_decrypted_game_eboot(path: Path) -> dict[str, int]:
    """Check header of user's own local PS4 ELF x86-64, without executing it.

    SCE-specific e_type is not a Win32 PE and does not prove that import
    resolution, patch sites, Vulkan, saves or gameplay work on this PC.
    """
    if not path.is_file() or path.is_symlink():
        raise PackageError('decrypted eboot must be a regular local game file')
    size = path.stat().st_size
    if size < 1024 * 1024 or size > 512 * 1024 * 1024:
        raise PackageError('decrypted eboot outside expected size range')
    with path.open('rb') as f:
        header = f.read(64)
    if len(header) != 64 or header[:4] != b'\x7fELF' or header[4:8] != b'\x02\x01\x01\x09':
        raise PackageError('expected PS4 ELF64 little-endian executable header')
    kind, machine = struct.unpack_from('<HH', header, 16)
    if machine != 0x3e or kind not in (0xfe00, 0xfe10):
        raise PackageError('expected x86-64 PS4 ELF executable kind')
    return {'elf_class': 64, 'machine_x86_64': 1, 'sce_elf_type': kind}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('package', type=Path, help='local Windows release ZIP or extracted folder')
    p.add_argument('--game-sfo', type=Path,
                   help='optional PRIVATE local sce_sys/param.sfo: verify CUSA03173 update 1.09')
    p.add_argument('--game-eboot', type=Path,
                   help='optional PRIVATE decrypted eboot ELF64; requires --game-sfo')
    p.add_argument('--write-manifest', type=Path, help='private local full per-file digest manifest')
    p.add_argument('--verify-manifest', type=Path, help='check against private prior manifest')
    args = p.parse_args(argv)
    try:
        if args.write_manifest and inside_dir(args.package, args.write_manifest):
            raise PackageError('manifest must be outside package directory')
        result = inspect(args.package)
        summary = result['summary']
        if args.game_sfo:
            read_game_sfo(args.game_sfo)
            summary['private_game_sfo_109_verified'] = True
            summary['game_eboot_patch_sites_verified'] = False
        if args.game_eboot:
            if not args.game_sfo:
                raise PackageError('--game-eboot requires matching --game-sfo')
            read_decrypted_game_eboot(args.game_eboot)
            summary['private_game_elf64_x86_64_verified'] = True
            summary['game_eboot_patch_sites_verified'] = False
        if args.verify_manifest:
            old = json.loads(args.verify_manifest.read_text(encoding='utf-8'))
            if old.get('schema') != MANIFEST_SCHEMA or old.get('files') != result['files']:
                raise PackageError('package differs from expected private runtime manifest')
            summary['manifest_verified'] = True
        if args.write_manifest:
            path = args.write_manifest
            path.parent.mkdir(parents=True, exist_ok=True)
            data = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            if len(data) > 4 * 1024**2:
                raise PackageError('private digest manifest exceeds 4 MiB budget')
            tmp = path.with_name(path.name + '.v185-tmp')
            try:
                with tmp.open('xb') as f:
                    f.write(data)
                os.replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)
            summary['private_manifest_written'] = True
        text = json.dumps(summary, sort_keys=True, ensure_ascii=False)
        if len(text.encode('utf-8')) > MAX_CONSOLE:
            raise PackageError('summary exceeds stdout budget')
        print(text)
        return 0
    except (PackageError, OSError, zipfile.BadZipFile, ValueError, UnicodeError,
            json.JSONDecodeError) as exc:
        # Never print local private paths, data, raw mismatches or Python backtraces.
        reason = str(exc) if isinstance(exc, PackageError) else 'unreadable/bad runtime or private manifest'
        print('V185_FAIL: ' + reason[:200], file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
