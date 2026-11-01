#!/usr/bin/env python3
"""V217: private resumable Win64 COFF from original full-game generated C.

Does not publish original-game code, addresses, binary objects or build logs.
Requires the V213 pinned upstream source with V195 patched rc.h and the
self-contained V214 public MinGW SDK. Native game boot is NOT proven.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import time
from bounded_private_subprocess_v210 import run_stage
import verify_coff_dependencies_v219 as deps

PIN = '8f31ec7c41f252730c6325d52647046baef7549f'
VALID = re.compile(r'recomp(?:_[0-9a-fA-F]{5})?\.c\Z')
MAX_SOURCE_BYTES = 64 * 1024**2
MAX_INDEX_BYTES = 2 * 1024**2

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def private(path: Path) -> Path:
    p = path.absolute()
    if p.is_symlink() or any((a / '.git').exists() for a in (p, *p.parents)):
        raise ValueError('private game files must stay outside Git')
    return p

def coff_ok(path: Path) -> bool:
    if not path.is_file() or path.is_symlink() or path.stat().st_size < 20:
        return False
    with path.open('rb') as f:
        header = f.read(20)
    machine, sections = struct.unpack_from('<HH', header)
    return machine == 0x8664 and 1 <= sections <= 32767

def prerequisites(generated: Path, upstream: Path, sdk_root: Path,
                  output: Path) -> tuple[Path, str, str]:
    private(generated)
    private(output)
    if not generated.is_dir() or not output.parent.is_dir():
        raise ValueError('generated source or private output parent missing')
    root = upstream.resolve(strict=True)
    if root.is_symlink() or not (root / '.git').exists():
        raise ValueError('missing pinned upstream source')
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                   timeout=10, stderr=subprocess.DEVNULL,
                                   text=True).strip()
    if head != PIN:
        raise ValueError('unreviewed original upstream version')
    sdk_root = sdk_root.resolve(strict=True)
    meta = sdk_root / 'manifest.json'
    if not meta.is_file() or meta.stat().st_size > 100000:
        raise ValueError('missing portable Win64 SDK metadata')
    manifest = json.loads(meta.read_text())
    if manifest.get('upstream') != PIN or manifest.get('format') != (
        'SHYT_V214_PUBLIC_WIN64_CROSS_HEADERS'
    ):
        raise ValueError('unreviewed Win64 cross SDK')
    if digest(root / 'src/recomp/rc.h') != manifest.get('patched_rc_sha256'):
        raise ValueError('wrong V195 patched original runtime header')
    header = sdk_root / 'include'
    for name in ('assert.h', 'stdint.h', 'string.h'):
        item = header / name
        if item.is_symlink() or not item.is_file():
            raise ValueError('portable SDK header is missing or broken symlink')
    if any(p.is_symlink() for p in header.rglob('*')):
        raise ValueError('portable SDK has nonportable external links')
    if shutil.disk_usage(output.parent).free < 1024**3:
        raise ValueError('insufficient private compilation storage')
    compiler = shutil.which('clang')
    if not compiler:
        raise ValueError('LLVM clang is required')
    return header, digest(meta), compiler

def compile_sources(generated: Path, upstream: Path, sdk: Path, output: Path,
                    names: list[str], opt: int = 0, budget_seconds: int = 45) -> dict:
    if opt not in (0, 1, 2) or not 1 <= len(names) <= 4:
        raise ValueError('unbounded file selection or optimization')
    if not 10 <= budget_seconds <= 3600:
        raise ValueError('invalid private per-invocation runtime budget')
    if any(not VALID.fullmatch(n) for n in names) or len(set(names)) != len(names):
        raise ValueError('unsafe/duplicate generated file names')
    generated, output = private(generated), private(output)
    header, sdk_hash, compiler = prerequisites(generated, upstream, sdk, output)
    output.mkdir(parents=True, exist_ok=True)
    index = output / 'private_coff_manifest_v217.json'
    if index.is_symlink() or (index.exists() and index.stat().st_size > MAX_INDEX_BYTES):
        raise ValueError('unsafe private manifest')
    saved = json.loads(index.read_text()) if index.exists() else {
        'format': 'SHYT_PRIVATE_ORIGINAL_COFF_V217', 'objects': {}}
    if saved.get('format') != 'SHYT_PRIVATE_ORIGINAL_COFF_V217' or not isinstance(
            saved.get('objects'), dict):
        raise ValueError('invalid private manifest')
    spec_base = {'upstream': PIN, 'sdk_manifest_sha256': sdk_hash,
                 'rc_header_sha256': digest(upstream / 'src/recomp/rc.h'),
                 'opt': opt, 'target': 'x86_64-w64-windows-gnu',
                 'clang_version': subprocess.check_output(
                     [compiler, '--version'], text=True, timeout=10).splitlines()[0]}
    # Old V217 manifests deliberately lack these keys and fail the reuse check.
    spec_base.update(deps.input_fingerprint(upstream,sdk,compiler))
    reused = compiled = 0
    started = time.monotonic()
    for name in names:
        if time.monotonic() - started >= budget_seconds - 5:
            break  # preserve completed per-object SHA-256 checkpoints
        source = generated / name
        if source.is_symlink() or not source.is_file() or not (
            1 <= source.stat().st_size <= MAX_SOURCE_BYTES):
            raise ValueError('missing/unsafe private original C shard')
        source_hash = digest(source)
        dest = output / (source.stem + '.obj')
        spec = {**spec_base, 'source_sha256': source_hash}
        previous = saved['objects'].get(name)
        if (previous and previous.get('spec') == spec and coff_ok(dest)
                and digest(dest) == previous.get('object_sha256')):
            reused += 1
            continue
        partial = output / (source.stem + '.obj.partial')
        if partial.exists() or partial.is_symlink():
            raise ValueError('stale partial object: inspect privately')
        command = [
            compiler, '--target=x86_64-w64-windows-gnu', '-std=gnu11',
            f'-O{opt}', '-ffp-contract=off', '-fno-strict-aliasing',
            '-Wno-unused', '-I' + str(upstream / 'src'),
            '-I' + str(upstream / 'deps/include'),
            '-isystem', str(header), '-c', str(source), '-o', str(partial)]
        try:
            for attempt in range(10):
                stage = ('coff_' + source.stem[-10:] + '_' +
                         source_hash[:7] + '_' + str(attempt))
                if not (output / 'logs' / (stage + '.summary.json')).exists():
                    break
            else:
                raise ValueError('too many private compile retries')
            remaining = budget_seconds - (time.monotonic() - started) - 2
            run_stage(command, stage, output / 'logs', timeout=max(1, min(600, remaining)))
            if not coff_ok(partial):
                raise ValueError('compiler did not create AMD64 COFF')
            os.replace(partial, dest)
            saved['objects'][name] = {
                'spec': spec, 'object_sha256': digest(dest),
                'bytes': dest.stat().st_size}
            staged = output / 'private_coff_manifest_v217.json.partial'
            if staged.exists() or staged.is_symlink():
                raise ValueError('stale partial manifest')
            staged.write_text(json.dumps(saved, indent=2) + '\n')
            os.replace(staged, index)
            compiled += 1
        except Exception:
            if partial.is_file() and not partial.is_symlink():
                partial.unlink()
            raise
    return {
        'selected_files': len(names), 'new_coff_objects': compiled,
        'reused_verified_coff_objects': reused,
        'deferred_files': len(names) - compiled - reused,
        'complete_game_boot_proven': False,
        'strict_no_guest_runtime_proven': False}

def selftest() -> None:
    assert not coff_ok(Path('/no-such-file'))
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'sample.obj'
        path.write_bytes(struct.pack('<HH', 0x8664, 3) + bytes(16))
        assert coff_ok(path)
        path.write_bytes(struct.pack('<HH', 0x14c, 3) + bytes(16))
        assert not coff_ok(path)
    # V218 rejects oversized and overlong interactive batches BEFORE preflight.
    for names, budget in [(['recomp.c'] * 5, 45), (['recomp.c'], 5)]:
        try:
            compile_sources(Path('nonexistent'), Path('nonexistent'),
                            Path('nonexistent'), Path('nonexistent'),
                            names, 0, budget)
        except ValueError:
            pass
        else:
            raise AssertionError('V218 interactive batch/time bounds bypassed')
    print('SHYT_V217_PRIVATE_AMD64_COFF_MANIFEST_SELFTEST_PASS')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--generated-dir', type=Path)
    ap.add_argument('--upstream', type=Path)
    ap.add_argument('--sdk', type=Path)
    ap.add_argument('--output-dir', type=Path)
    ap.add_argument('--file', action='append', default=[])
    ap.add_argument('--opt', type=int, default=0)
    ap.add_argument('--budget-seconds', type=int, default=45)
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    if args.self_test:
        selftest()
    else:
        if not all([args.generated_dir, args.upstream, args.sdk,
                    args.output_dir, args.file]):
            ap.error('pass original private generated dir, upstream, SDK, output and --file')
        try:
            result = compile_sources(args.generated_dir, args.upstream,
                                     args.sdk, args.output_dir,
                                     args.file, args.opt, args.budget_seconds)
            print(json.dumps(result, separators=(',', ':')))
        except (OSError, ValueError, subprocess.SubprocessError,
                RuntimeError):
            ap.error('private original COFF failed; inspect bounded LOCAL logs')
