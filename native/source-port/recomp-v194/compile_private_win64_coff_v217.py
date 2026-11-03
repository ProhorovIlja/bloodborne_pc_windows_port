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
    # V344: full-game generated C/COFF must never be redirected through
    # an ancestor symlink/junction into a public Git checkout.
    canonical = p.resolve(strict=False)
    lexical = (p, *p.parents)
    actual = (canonical, *canonical.parents)
    if (any(a.is_symlink() for a in lexical) or
            any((a / '.git').exists() for a in (*lexical, *actual))):
        raise ValueError('private game files must stay outside Git and path aliases')
    return p

def coff_ok(path: Path) -> bool:
    """V281: structural AMD64 COFF object check, not four-byte magic.

    A valid-looking machine+section prefix alone is insufficient:
    truncated objects would previously be counted as successful
    original-game AOT modules. Validate all section extents, relocations,
    symbol entries and string table *without* reading private code.
    This checks structural closure, not relocatable symbol resolution.
    """
    if (path.is_symlink() or not path.is_file() or
            not 82 <= path.stat().st_size <= 256*1024**2):
        return False
    size=path.stat().st_size
    try:
        with path.open('rb') as stream:
            header=stream.read(20)
            if len(header)!=20:
                return False
            machine,sections,_,symbols,nsyms,optional,_=struct.unpack(
                '<HHLLLHH',header)
            # Compiled COFF .obj, NOT linked PE/EXE (which has MZ header).
            if (machine!=0x8664 or not 1<=sections<=32767 or
                    optional!=0 or symbols<20+40*sections or
                    nsyms<1 or nsyms>(size-symbols)//18):
                return False
            section_end=20+40*sections
            if section_end>size:
                return False
            # V300: COFF relocations must reference PRIMARY symbol entries.
            # An index into an 18-byte auxiliary record is in range but
            # cannot be linked. Track only auxiliary ordinals in a compact
            # bitset, without reading or logging private symbol names.
            symbol_end=symbols+nsyms*18
            if symbol_end>size-4:
                return False
            auxiliary_slots=bytearray((nsyms+7)//8)
            stream.seek(symbols)
            ordinal=0
            while ordinal<nsyms:
                entry=stream.read(18)
                if len(entry)!=18:
                    return False
                extra=entry[17]
                if ordinal+extra>=nsyms:
                    return False
                for aux_ordinal in range(ordinal+1,ordinal+extra+1):
                    auxiliary_slots[aux_ordinal>>3]|=1<<(aux_ordinal&7)
                if extra:
                    stream.seek(extra*18,1)
                ordinal+=extra+1
            stream.seek(20)
            for _ in range(sections):
                data=stream.read(40)
                if len(data)!=40:
                    return False
                raw_size,raw_at,reloc_at,_,nreloc,_=struct.unpack_from(
                    '<LLLLHH',data,16)
                characteristics=struct.unpack_from('<I',data,36)[0]
                if raw_size and (raw_at<section_end or
                                 raw_at>symbols or raw_size>symbols-raw_at):
                    return False
                # V293: COFF AMD64 relocation count can legitimately
                # overflow 16 bits for large original-game AOT shards.
                # The IMAGE_SCN_LNK_NRELOC_OVFL flag (0x01000000)
                # demands a first dummy relocation whose VA contains
                # the real count INCLUDING that dummy record.
                overflow=bool(characteristics & 0x01000000)
                if overflow != (nreloc==0xffff):
                    return False
                relocation_count=nreloc
                if nreloc:
                    if reloc_at<section_end or reloc_at>symbols:
                        return False
                    if overflow:
                        if symbols-reloc_at<10:
                            return False
                        pos=stream.tell()
                        stream.seek(reloc_at)
                        dummy=stream.read(10)
                        stream.seek(pos)
                        relocation_count,index,kind=struct.unpack('<LLH',dummy)
                        if (relocation_count<=0xffff or
                                index!=0 or kind!=0):
                            return False
                    if (relocation_count>1_000_000 or
                            relocation_count>(symbols-reloc_at)//10):
                        return False
                    # No private code is read. Relocation metadata is
                    # checked for missing original COFF symbol entries.
                    # A bad symbol ordinal otherwise survives V275 cache
                    # verification and only fails at final Windows link.
                    pos=stream.tell()
                    stream.seek(reloc_at+(10 if overflow else 0))
                    for _ in range(relocation_count-(1 if overflow else 0)):
                        raw=stream.read(10)
                        if len(raw)!=10:
                            return False
                        _,symbol_index,rel_type=struct.unpack('<LLH',raw)
                        if (symbol_index>=nsyms or rel_type>0x10 or
                                auxiliary_slots[symbol_index>>3] &
                                (1<<(symbol_index&7))):
                            return False
                    stream.seek(pos)
            string_at=symbols+nsyms*18
            if string_at>size-4:
                return False
            stream.seek(string_at)
            string_bytes=stream.read(4)
            if len(string_bytes)!=4:
                return False
            string_size=struct.unpack('<L',string_bytes)[0]
            return 4<=string_size<=size-string_at
    except (OSError,ValueError,struct.error,OverflowError):
        return False

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
        # V297: the former self-test used only 20 fake header bytes.
        # V281/V293 correctly reject that as truncated COFF. Build one
        # complete synthetic AMD64 object, no original-game bytes.
        header = struct.pack('<HHLLLHH',0x8664,1,0,60,1,0,0)
        section = struct.pack('<8sLLLLLLHHL',
                              b'.text\0\0\0',0,0,0,0,0,0,0,0,0)
        symbol = struct.pack('<8sLhHBB',b'fixture\0',0,1,0x20,2,0)
        valid = header+section+symbol+struct.pack('<L',4)
        assert len(valid)==82
        path.write_bytes(valid)
        assert coff_ok(path)
        path.write_bytes(valid[:20])
        assert not coff_ok(path)
        path.write_bytes(struct.pack('<H',0x14c)+valid[2:])
        assert not coff_ok(path)
        path.write_bytes(valid)
        assert coff_ok(path)
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
