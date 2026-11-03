#!/usr/bin/env python3
"""V212 offline fail-closed prerequisites for the PRIVATE full Bloodborne 1.09 AOT.

No original bytes, paths, raw symbols or SHA fingerprints in printed status.
Checks cannot prove a native working game, nor exact source->binary provenance.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

PIN = '8f31ec7c41f252730c6325d52647046baef7549f'
MARKERS = ('SHYT_NATIVE_V199_GUEST_RET_FLAGS_FLUSH',
           'SHYT_NATIVE_V200_INDIRECT_CALL_NATIVE_DISPATCH',
           'SHYT_NATIVE_V201_INDIRECT_JMP_NATIVE_DISPATCH',
           'SHYT_NATIVE_V203_GENERIC_TAIL_DIRECT_AOT')

def file_check(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError('decrypted PS4 ELF missing or unsafe')
    size = path.stat().st_size
    if not 1_000_000 <= size <= 512 * 1024**2:
        raise ValueError('original ELF size not plausible')
    with path.open('rb') as stream:
        hdr = stream.read(64)
        if len(hdr) != 64 or hdr[:7] != b'\x7fELF\x02\x01\x01':
            raise ValueError('input is not decrypted little-endian ELF64')
        typ, mach = struct.unpack_from('<HH', hdr, 16)
        if typ != 0xFE10 or mach != 62:
            raise ValueError('expected PS4 x86-64 executable, not ordinary PC ELF')
        phoff, phsize, phnum = (struct.unpack_from('<Q', hdr, 32)[0],
                                struct.unpack_from('<H', hdr, 54)[0],
                                struct.unpack_from('<H', hdr, 56)[0])
        if phsize != 56 or not 1 <= phnum <= 64 or phoff + phsize * phnum > size:
            raise ValueError('malformed PS4 ELF program table')
        stream.seek(phoff)
        headers = [struct.unpack('<IIQQQQQQ', stream.read(56)) for _ in range(phnum)]
        if any(h[2] + h[5] > size for h in headers):
            raise ValueError('invalid ELF segment file bounds')
        execs = [h for h in headers if h[0] == 1 and h[1] & 1]
        eh = [h for h in headers if h[0] == 0x6474E550]
        if len(execs) != 1 or len(eh) != 1 or eh[0][5] < 12:
            raise ValueError('expected a single executable and FDE header segment')
        stream.seek(eh[0][2])
        if stream.read(4) != b'\x01\x1b\x03\x3b':
            raise ValueError('unexpected FDE header encoding')
        stream.read(4)
        count = struct.unpack('<I', stream.read(4))[0]
        if count < 1 or 12 + count * 8 > eh[0][5]:
            raise ValueError('invalid FDE index size')
    return {'ps4_elf64_header_valid': True, 'original_bytes': size,
            'fde_entries_declared': count, 'fde_entries_fully_verified': False}

def upstream_check(root: Path) -> dict:
    if root.is_symlink() or not (root / '.git').exists():
        raise ValueError('upstream git checkout is missing or unsafe')
    try:
        head = subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', 'HEAD'],
            text=True, timeout=10, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        raise ValueError('could not verify pinned source commit') from None
    if head != PIN:
        raise ValueError('wrong upstream commit; do not use an unreviewed generator')
    src = root / 'tools/recomp/bbrecomp.c'
    scan = root / 'tools/recomp/scan.c'
    if any(p.is_symlink() or not p.is_file() for p in (src, scan)):
        raise ValueError('generator/scanner source missing')
    code = src.read_text(encoding='utf-8')
    if any(marker not in code for marker in MARKERS):
        raise ValueError('required native AOT generator patches are not applied')
    for exe, source in ((root / 'out/recomp/bbrecomp', src),
                        (root / 'out/recomp/scan', scan)):
        if exe.is_symlink() or not exe.is_file() or not os.access(exe, os.X_OK):
            raise ValueError('original tools must be built before private full scan')
        if exe.stat().st_mtime_ns < source.stat().st_mtime_ns:
            raise ValueError('generator/scanner binary predates source; rebuild tools')
    for script in ('ps4elf.py', 'pointers.py', 'imports.py', 'import_names.inc'):
        if not (root / 'tools/recomp' / script).is_file():
            raise ValueError('essential upstream source tool missing')
    return {'upstream_git_pin_valid': True,
            'native_generator_patches_present': True,
            'scanner_and_generator_executable': True,
            'binary_source_provenance_fully_proven': False}

def check(eboot: Path, work: Path | None, upstream: Path | None,
          min_free_gib: int) -> dict:
    result = file_check(eboot)
    result['upstream_checked'] = upstream is not None
    if upstream:
        result.update(upstream_check(upstream))
    result['disk_checked'] = work is not None
    if work:
        if work.is_symlink() or any((p / '.git').exists()
                                    for p in (work, *work.parents)):
            raise ValueError('private output must be outside source repositories')
        ancestor = next((p for p in (work, *work.parents) if p.exists()), None)
        if not ancestor or not ancestor.is_dir():
            raise ValueError('private workspace parent not found')
        result['free_disk_threshold_met'] = (
            shutil.disk_usage(ancestor).free >= min_free_gib * 1024**3)
        if not result['free_disk_threshold_met']:
            raise ValueError('insufficient free storage for full private AOT batch')
    result['ready_to_start_private_full_scan'] = bool(upstream and work)
    result['native_game_boot_proven'] = False
    return result

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--eboot', type=Path, required=True)
    p.add_argument('--work', type=Path)
    p.add_argument('--upstream', type=Path)
    p.add_argument('--min-free-gib', type=int, default=16)
    o = p.parse_args()
    if not 1 <= o.min_free_gib <= 1024:
        p.error('invalid free space threshold')
    try:
        result = check(o.eboot, o.work, o.upstream, o.min_free_gib)
    except (OSError, ValueError, struct.error) as exc:
        p.error(str(exc))
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))

if __name__ == '__main__':
    main()
