#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V377: bounded STATIC ABI/import checks for own native PE64 / Linux ELF64.

This is one of many closure gates, NEVER proof of a playable game or zero
runtime PS4 guest code: a binary can dlopen/load arbitrary data at runtime.
No game-owned source, executable, addresses, symbols or logs are emitted.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import struct
import sys

MAX_BYTES = 512 * 1024 * 1024
MAX_SECTIONS = 96
MAX_IMPORTS = 256
MAX_PHDRS = 128
BAD_TOKENS = ('eboot', 'shadps4', 'orbis', 'libsce', 'ps4', 'scegnm',
              'vkd3d-proton', 'dxvk', 'wine', 'proton', 'ps4emu')
WINDOWS_DLLS = frozenset(('kernel32.dll', 'kernelbase.dll', 'user32.dll',
    'gdi32.dll', 'advapi32.dll', 'shell32.dll', 'ole32.dll', 'combase.dll',
    'comdlg32.dll', 'imm32.dll', 'ntdll.dll', 'msvcrt.dll', 'ucrtbase.dll',
    'vcruntime140.dll', 'vcruntime140_1.dll', 'd3d12.dll', 'dxgi.dll',
    'd3dcompiler_47.dll', 'vulkan-1.dll', 'winmm.dll', 'avrt.dll',
    'ws2_32.dll', 'bcrypt.dll', 'mfplat.dll', 'mfreadwrite.dll',
    'xinput1_4.dll', 'sdl3.dll', 'openal32.dll'))
LINUX_PREFIXES = ('libc.so.', 'libm.so.', 'libdl.so.', 'librt.so.',
    'libpthread.so.', 'libgcc_s.so.', 'libstdc++.so.', 'libvulkan.so.',
    'libsdl3.so.', 'libz.so.', 'libzstd.so.', 'libasound.so.',
    'libavcodec.so.', 'libavformat.so.', 'libavutil.so.',
    'libswresample.so.', 'libx11.so.', 'libxcb.so.', 'libwayland-',
    'libdrm.so.', 'libatomic.so.', 'libunwind.so.', 'libxkbcommon.so.')

class NotNative(ValueError):
    pass

def within(start: int, size: int, length: int) -> bool:
    return 0 <= start <= length and 0 <= size <= length - start

def u16(data: bytes, at: int) -> int:
    if not within(at, 2, len(data)):
        raise NotNative('truncated integer')
    return struct.unpack_from('<H', data, at)[0]

def u32(data: bytes, at: int) -> int:
    if not within(at, 4, len(data)):
        raise NotNative('truncated integer')
    return struct.unpack_from('<I', data, at)[0]

def u64(data: bytes, at: int) -> int:
    if not within(at, 8, len(data)):
        raise NotNative('truncated integer')
    return struct.unpack_from('<Q', data, at)[0]

def ascii_cstr(data: bytes, start: int, maxlen: int = 256) -> str:
    if not within(start, 1, len(data)):
        raise NotNative('invalid string')
    end = data.find(b'\0', start, min(len(data), start + maxlen))
    if end <= start:
        raise NotNative('unbounded or empty string')
    raw = data[start:end]
    if any(b < 32 or b > 126 for b in raw):
        raise NotNative('non-printable import')
    return raw.decode('ascii')

def approved(lib: str, target: str) -> bool:
    name = lib.lower()
    if any(t in name for t in BAD_TOKENS) or '/' in name or '\\' in name or '..' in name:
        return False
    if target == 'windows':
        return name in WINDOWS_DLLS or name.startswith(('api-ms-win-', 'ext-ms-win-'))
    return any(name.startswith(s) for s in LINUX_PREFIXES)

def pe64(data: bytes) -> dict:
    size = len(data)
    if size < 512 or data[:2] != b'MZ':
        raise NotNative('not an x64 PE executable')
    coff = u32(data, 0x3c)
    if coff < 64 or coff > 65536 or not within(coff, 24, size) or data[coff:coff+4] != b'PE\0\0':
        raise NotNative('invalid PE header')
    machine, sections, _, _, _, optional, flags = struct.unpack_from('<HHLLLHH', data, coff + 4)
    if machine != 0x8664 or not 1 <= sections <= MAX_SECTIONS or not 0x70 <= optional <= 4096:
        raise NotNative('unsupported PE architecture')
    if flags & 0x2000:
        raise NotNative('DLL is not a standalone program')
    opt = coff + 24
    if not within(opt, optional + sections*40, size) or u16(data, opt) != 0x20b:
        raise NotNative('not PE32+ x64')
    entry = u32(data, opt + 0x10)
    image_size = u32(data, opt + 0x38)
    header_size = u32(data, opt + 0x3c)
    nrva = u32(data, opt + 0x6c)
    if not entry or not 0 < image_size <= 0x7fffffff or not 0 < header_size <= size:
        raise NotNative('invalid executable entry')
    if nrva > 64 or (nrva > 1 and optional < 0x80):
        raise NotNative('invalid import directory layout')
    table = opt + optional
    ranges: list[tuple[int, int, int, bool]] = []
    for j in range(sections):
        at = table+j*40
        vsize = u32(data, at+8)
        rva = u32(data, at+12)
        rawsize = u32(data, at+16)
        raw = u32(data, at+20)
        characteristics = u32(data, at+36)
        if not rva or not within(raw, rawsize, size) or rawsize == 0:
            raise NotNative('invalid executable section')
        if rva+max(vsize, rawsize) > image_size:
            raise NotNative('section exceeds image')
        ranges.append((rva, rawsize, raw, bool(characteristics & 0x20000000)))
    if not any(base <= entry < base+length and executable for base, length, _, executable in ranges):
        raise NotNative('entry is not executable')
    def convert(rva: int, minimum: int) -> int:
        if rva < header_size and within(rva, minimum, header_size):
            return rva
        for base, length, raw, _ in ranges:
            if base <= rva and within(rva-base, minimum, length):
                return raw+rva-base
        raise NotNative('import RVA outside file-backed sections')
    imports: list[str] = []
    if nrva > 1:
        irva, isize = u32(data, opt+0x78), u32(data, opt+0x7c)
        if (irva == 0) != (isize == 0):
            raise NotNative('partial import directory')
        if irva:
            if isize < 40 or isize > MAX_IMPORTS*20+20:
                raise NotNative('unbounded import directory')
            at = convert(irva, isize)
            ended = False
            for offset in range(0, isize-19, 20):
                original, stamp, forward, name, thunk = struct.unpack_from('<IIIII',data,at+offset)
                if original == stamp == forward == name == thunk == 0:
                    ended=True
                    break
                if not name:
                    raise NotNative('unnamed PE import')
                imports.append(ascii_cstr(data, convert(name, 1)))
                if len(imports)>MAX_IMPORTS:
                    raise NotNative('too many imports')
            if not ended:
                raise NotNative('unterminated import directory')
    if any(not approved(i,'windows') for i in imports):
        raise NotNative('unreviewed native import')
    return {'target':'windows','native_container_verified':True,
            'imports_reviewed':len(imports),'unknown_imports':0,
            'runtime_no_guest_proven':False,'whole_game_boot_proven':False}

def elf64(data: bytes) -> dict:
    size=len(data)
    if size<64 or data[:7]!=b'\x7fELF\x02\x01\x01':
        raise NotNative('not a little-endian x86-64 ELF')
    kind,machine = u16(data,16),u16(data,18)
    if kind not in (2,3) or machine!=62 or u64(data,24)==0:
        raise NotNative('not a native x86-64 ELF executable')
    phoff,phsize,phnum=u64(data,32),u16(data,54),u16(data,56)
    if phsize!=56 or not 1<=phnum<=MAX_PHDRS or not within(phoff,phsize*phnum,size):
        raise NotNative('unsafe ELF program headers')
    loads:list[tuple[int,int,int,int]]=[]
    dynamic:list[tuple[int,int]]=[]
    executable=False
    interp=[]
    entry=u64(data,24)
    for i in range(phnum):
        at=phoff+i*56
        typ,flags,off,addr,_,filebytes,memsize,_=struct.unpack_from('<IIQQQQQQ',data,at)
        if typ in (1,2,3):
            if not within(off,filebytes,size) or memsize < filebytes:
                raise NotNative('ELF segment exceeds file')
        if typ==1:
            loads.append((addr,filebytes,off,memsize))
            if (flags&1) and addr<=entry<addr+filebytes:
                executable=True
        elif typ==2:
            if filebytes%16 or filebytes>65536:
                raise NotNative('invalid ELF dynamic array')
            dynamic.append((off,filebytes))
        elif typ==3:
            interp.append(ascii_cstr(data,off,256))
    if not executable or len(interp)>1 or len(dynamic)>1:
        raise NotNative('not a native executable with bounded segments')
    if interp and not (interp[0].startswith('/lib64/ld-linux-x86-64.so.') or
                        interp[0].startswith('/lib/x86_64-linux-gnu/ld-linux-x86-64.so.')):
        raise NotNative('unknown dynamic loader')
    def virt_to_file(addr:int, bytes_needed:int)->int:
        for base,filesz,off,_ in loads:
            if addr>=base and within(addr-base,bytes_needed,filesz):
                return off+addr-base
        raise NotNative('ELF dynamic string address invalid')
    needed:list[int]=[]
    strtab=strsz=0
    if dynamic:
        off,length=dynamic[0]
        terminated=False
        for at in range(off,off+length,16):
            tag,value=struct.unpack_from('<qQ',data,at)
            if tag==0:
                terminated=True
                break
            if tag==1: needed.append(value)
            elif tag==5: strtab=value
            elif tag==10: strsz=value
            elif tag in (15,29):
                raise NotNative('rpath requires explicit review')
        if not terminated or len(needed)>MAX_IMPORTS:
            raise NotNative('bad or unbounded ELF dynamic array')
    imports=[]
    if needed:
        if not strtab or not 1<=strsz<=1024*1024:
            raise NotNative('ELF dynamic string table missing')
        strings=virt_to_file(strtab,strsz)
        for name in needed:
            if name>=strsz:
                raise NotNative('ELF import string outside table')
            lib=ascii_cstr(data,strings+name)
            if name+len(lib)+1>strsz:
                raise NotNative('ELF import overruns string table')
            imports.append(lib)
    if any(not approved(i,'linux') for i in imports):
        raise NotNative('unreviewed native dependency')
    return {'target':'linux','native_container_verified':True,
            'imports_reviewed':len(imports),'unknown_imports':0,
            'runtime_no_guest_proven':False,'whole_game_boot_proven':False}

def inspect_bytes(data:bytes,target:str)->dict:
    if not 64<=len(data)<=MAX_BYTES:
        raise NotNative('binary size outside budget')
    if target=='windows': return pe64(data)
    if target=='linux': return elf64(data)
    raise NotNative('unreviewed architecture')

def inspect_path(path:Path,target:str)->dict:
    if path.is_symlink() or not path.is_file() or not 64<=path.stat().st_size<=MAX_BYTES:
        raise NotNative('unsafe executable input')
    return inspect_bytes(path.read_bytes(),target)

def cli()->None:
    parser=argparse.ArgumentParser(description='V377 bounded native PE/ELF static preflight; NOT whole-game proof')
    parser.add_argument('--target',choices=('windows','linux'))
    parser.add_argument('--binary',type=Path)
    args=parser.parse_args()
    if not args.target or args.binary is None:
        parser.error('provide --target and --binary')
    try:
        print(json.dumps(inspect_path(args.binary,args.target),sort_keys=True,separators=(',',':')))
    except (NotNative, OSError,struct.error):
        print('NATIVE_V377_FAIL_CLOSED_STATIC_BINARY_PREFLIGHT',file=sys.stderr)
        raise SystemExit(2) from None
if __name__=='__main__': cli()
