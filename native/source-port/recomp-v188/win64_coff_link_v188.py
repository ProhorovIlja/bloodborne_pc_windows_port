#!/usr/bin/env python3
"""Compile private upstream-style generated C chunks to an x64 PE DLL.

This is a *toolchain experiment*, not a full Bloodborne recompile. Never
reads, prints, publishes or uploads source/game contents. The original
macOS ARM64 generator does not become Windows-compatible just by linking.
Generated source remains on the user's machine; no original ELF is loaded.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

class BuildError(Exception):
    pass

NAME = re.compile(r"recomp(?:_[0-9]+)?\.c\Z")
MAX_SOURCES = 512
MAX_UNIT = 64 << 20
MAX_TOTAL = 3 << 30
MAX_OUTPUT = 900 << 20


def sources_in(source_dir: Path) -> list[Path]:
    if source_dir.is_symlink() or not source_dir.is_dir():
        raise BuildError("source directory missing or symlink")
    files = sorted(source_dir.iterdir(), key=lambda p: p.name)
    sources = [f for f in files if NAME.fullmatch(f.name)]
    if len(sources) > MAX_SOURCES or not any(f.name == "recomp.c" for f in sources):
        raise BuildError("invalid generated source list or source count limit")
    total = 0
    for p in sources:
        if p.is_symlink() or not p.is_file():
            raise BuildError("generated source must be a regular non-symlink file")
        size = p.stat().st_size
        if not size or size > MAX_UNIT:
            raise BuildError("generated source size exceeded")
        total += size
        if total > MAX_TOTAL:
            raise BuildError("generated source set exceeds local compile budget")
    return sources


def run_command(command: list[str], phase: str) -> None:
    try:
        result = subprocess.run(command, capture_output=True, timeout=240, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BuildError(f"{phase}: compiler unavailable or time limit exceeded") from exc
    if result.returncode:
        # Deliberately not printing stderr: generated game C is private.
        raise BuildError(f"{phase}: compiler/linker exited {result.returncode}; inspect privately")


def read_pe_exports(path: Path) -> bool:
    """Check x64 DLL and presence of named export without loading the module."""
    def at(file, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > file_size:
            raise BuildError("invalid PE bounds")
        file.seek(offset)
        chunk = file.read(size)
        if len(chunk) != size:
            raise BuildError("short PE read")
        return chunk
    file_size = path.stat().st_size
    if file_size < 512 or file_size > MAX_OUTPUT:
        raise BuildError("invalid DLL size")
    with path.open('rb') as file:
        dos = at(file, 0, 64)
        if dos[:2] != b'MZ':
            raise BuildError("expected Windows PE DLL")
        pe_off = struct.unpack_from('<I', dos, 0x3c)[0]
        header = at(file, pe_off, 24)
        if header[:4] != b'PE\0\0':
            raise BuildError("not a valid PE image")
        machine, sections, _, _, _, opt_size, characteristics = struct.unpack_from('<HHIIIHH', header, 4)
        if machine != 0x8664 or not 1 <= sections <= 96 or not characteristics & 0x2000:
            raise BuildError("expected AMD64 DLL machine and flags")
        optional = at(file, pe_off + 24, opt_size)
        if len(optional) < 120 or struct.unpack_from('<H', optional)[0] != 0x20b:
            raise BuildError("expected PE32+ optional header")
        rva, export_size = struct.unpack_from('<II', optional, 112)
        if not rva or export_size < 40:
            raise BuildError("missing Windows DLL export directory")
        table = at(file, pe_off + 24 + opt_size, 40 * sections)
        def rva_offset(value):
            for i in range(sections):
                data = table[40*i:40*(i+1)]
                vsize, va, rawsize, rawptr = struct.unpack_from('<IIII', data, 8)
                if va <= value < va + min(max(vsize, rawsize), 0x40000000) and value - va < rawsize:
                    return rawptr + value - va
            raise BuildError("export RVA outside file-backed sections")
        export = at(file, rva_offset(rva), 40)
        names, name_addresses = struct.unpack_from('<II', export, 24)[0], struct.unpack_from('<I', export, 32)[0]
        if not 1 <= names <= 256:
            raise BuildError("unexpected DLL export count")
        name_offsets = at(file, rva_offset(name_addresses), names * 4)
        for i in range(names):
            name_rva = struct.unpack_from('<I', name_offsets, i*4)[0]
            raw = at(file, rva_offset(name_rva), 64)
            if raw.split(b'\0', 1)[0] == b'bb_recomp_init':
                return True
        raise BuildError("missing bb_recomp_init DLL export")


def compile_win64(source_dir: Path, out: Path, include_dirs: list[Path],
                  clang: str = 'clang-cl', linker: str = 'lld-link') -> dict:
    source_dir = source_dir.resolve(strict=True)
    out = out.absolute()
    sources = sources_in(source_dir)
    if out.suffix.lower() != '.dll' or not out.parent.is_dir():
        raise BuildError("output must be an existing local directory's .dll file")
    if out.resolve().is_relative_to(source_dir):
        raise BuildError("DLL output cannot be inside private generated C source directory")
    for path in include_dirs:
        if path.is_symlink() or not path.is_dir():
            raise BuildError("include directory missing or symlink")
    if shutil.which(clang) is None or shutil.which(linker) is None:
        raise BuildError("clang-cl and lld-link must be installed and on PATH")
    with tempfile.TemporaryDirectory(prefix='v188-private-obj-', dir=out.parent) as tmp:
        root = Path(tmp)
        objects = []
        for i, source in enumerate(sources):
            obj = root / f'{i:04d}.obj'
            command = [clang, '/nologo', '/TC', '/std:c11', '/O2', '/W0', '/c',
                       *['/I'+str(p) for p in include_dirs], '/Fo'+str(obj), str(source)]
            run_command(command, f'COFF unit {i+1}/{len(sources)}')
            with obj.open('rb') as h:
                if h.read(2) != b'\x64\x86':
                    raise BuildError('compiler did not emit x86-64 COFF object')
            objects.append(obj)
        candidate = root / 'candidate.dll'
        command = [linker, '/NOLOGO', '/DLL', '/NOENTRY', '/NODEFAULTLIB',
                   '/MACHINE:X64', '/EXPORT:bb_recomp_init', '/OUT:'+str(candidate)]
        command.extend(map(str, objects))
        run_command(command, 'Win64 DLL link')
        read_pe_exports(candidate)
        os.replace(candidate, out)
    return {'kind':'coff-win64-v188','source_units_compiled':len(sources),
            'pe32_plus_amd64':True,'bb_recomp_init_export_present':True,
            'contains_actual_bloodborne_game_code_in_ci':False,
            'full_windows_game_port_proven':False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--source-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--include-dir', type=Path, action='append', default=[])
    p.add_argument('--clang-cl', default='clang-cl')
    p.add_argument('--lld-link', default='lld-link')
    a = p.parse_args(argv)
    try:
        report = compile_win64(a.source_dir, a.out, a.include_dir, a.clang_cl, a.lld_link)
    except (BuildError, ValueError, OSError) as error:
        # Compiler and file paths may be private. Never return them in output.
        print(json.dumps({'kind':'coff-win64-v188','status':'failure',
              'reason':str(error)[:160] if isinstance(error, BuildError) else 'invalid local inputs'}))
        return 2
    print(json.dumps(report, separators=(',', ':')))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
