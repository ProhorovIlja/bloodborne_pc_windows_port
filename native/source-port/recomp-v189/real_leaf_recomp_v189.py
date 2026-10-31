#!/usr/bin/env python3
"""Offline, fail-closed, user-local REAL Bloodborne 1.09 scalar leaf AOT proof.

Generated C/COFF/DLL and original executable must never be uploaded or committed.
Matches only explicitly supported true function starts in .eh_frame_hdr and
validates the complete clean game loaded-image digest before generating code.
Does not parse or execute branches, calls, pointers, platform APIs or TLS.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import mmap
from pathlib import Path
import platform
import random
import re
import struct
import subprocess
import sys

# Public clean 1.09 loaded-image reference in upstream bbport/scripts/game_check.py
IMAGE_SHA = '071df19c8880086d97182dbc057bc8cb37badaca57d9112683836b24a0444c0a'
EXPECTED_SIZE = 91042036
MAX_ELF_BYTES = 130 << 20
MAX_FDE = 250000
MAX_FUNCTION_BYTES = 64
# Restrict to arithmetic or identity, with all paths ending in ret.
PATTERNS = ('zero32', 'imm32', 'identity64', 'identity32')

class ProofError(Exception):
    pass


def load_original(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ProofError('regular decrypted ELF needed')
    if not 64 <= path.stat().st_size <= MAX_ELF_BYTES:
        raise ProofError('original executable size outside bounds')
    data = path.read_bytes()
    if data[:4] != b'\x7fELF' or data[4:7] != b'\x02\x01\x01':
        raise ProofError('expected little-endian ELF64 game input')
    kind, machine = struct.unpack_from('<HH', data, 16)
    if kind != 0xfe10 or machine != 62:
        raise ProofError('expected original PS4 x86-64 executable')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    phentsize, phnum = struct.unpack_from('<HH', data, 54)
    if phentsize != 56 or not 2 <= phnum <= 64 or phoff+phnum*56 > len(data):
        raise ProofError('unsafe program header directory')
    ph = [struct.unpack_from('<IIQQQQQQ', data, phoff+56*i) for i in range(phnum)]
    loadable = [p for p in ph if p[0] == 1]
    if len(loadable) != 2:
        raise ProofError('unsupported original image layout')
    end = 0
    for p in loadable:
        _, flags, offset, vaddr, _, filesz, memsz, _ = p
        if offset+filesz > len(data) or memsz < filesz or vaddr+memsz > EXPECTED_SIZE:
            raise ProofError('untrusted ELF segments')
        end = max(end, vaddr+memsz)
    if end != EXPECTED_SIZE:
        raise ProofError('unsupported 1.09 image length')
    image = bytearray(end)
    for p in loadable:
        _, _, offset, vaddr, _, filesz, _, _ = p
        image[vaddr:vaddr+filesz] = data[offset:offset+filesz]
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA:
        raise ProofError('unsupported game image SHA-256')
    eh = [p for p in ph if p[0] == 0x6474e550]
    if len(eh) != 1:
        raise ProofError('expected one ELF EH-frame header')
    p=eh[0]
    _, _, offset, vaddr, _, filesz, _, _ = p
    if filesz < 12 or offset+filesz > len(data) or data[offset:offset+4] != b'\x01\x1b\x03\x3b':
        raise ProofError('unexpected EH-frame encoding')
    count = struct.unpack_from('<I', data, offset+8)[0]
    if not 1000 < count <= MAX_FDE or 12+count*8 > filesz:
        raise ProofError('unexpected EH-frame function count')
    starts=[]
    for i in range(count):
        relative, fde = struct.unpack_from('<ii',data,offset+12+i*8)
        start=vaddr+relative
        if not 0xa0 <= start < loadable[0][6] or (starts and start<=starts[-1]):
            raise ProofError('untrusted function boundaries')
        starts.append(start)
    return bytes(image), starts


def identify(body: bytes):
    """Allow four total, straight-line scalar instruction forms, before any padding."""
    if body.startswith(b'\x31\xc0\xc3') or body.startswith(b'\x33\xc0\xc3'):
        return 'zero32', 3, 0
    if len(body)>=6 and body[0] == 0xb8 and body[5] == 0xc3:
        return 'imm32',6,struct.unpack_from('<I',body,1)[0]
    if body.startswith(b'\x48\x89\xf8\xc3'):
        return 'identity64',4,0
    if body.startswith(b'\x89\xf8\xc3'):
        return 'identity32',3,0
    return None


def select(image: bytes, starts: list[int]):
    found={}
    for a,b in zip(starts,starts[1:]):
        if b-a <= 0 or b-a > MAX_FUNCTION_BYTES or b > len(image):
            continue
        hit=identify(image[a:b])
        if hit is None:continue
        kind, size, imm=hit
        # Verify the remainder of this EH-frame interval is *only* alignment
        # instructions, not reachable instructions behind the first RET.
        pad = image[a+size:b]
        canonical_nop = b'\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00'
        is_padding = (not pad or all(x == 0x90 for x in pad) or
                      (0 <= len(pad)-len(canonical_nop) <= 6 and
                       pad == b'\x66'*(len(pad)-len(canonical_nop)) + canonical_nop))
        if b-a != 16 or not is_padding:
            continue
        if kind not in found:
            found[kind]=(a,size,imm,bytes(image[a:a+size]))
        if len(found)==len(PATTERNS):break
    if set(found)!=set(PATTERNS):
        raise ProofError('required executable function kinds absent')
    return [found[kind] for kind in PATTERNS]


def expected(kind: str, arg: int, imm: int) -> int:
    if kind == 'zero32':return 0
    if kind == 'imm32':return imm
    if kind == 'identity64':return arg & 0xffffffffffffffff
    if kind == 'identity32':return arg & 0xffffffff
    raise AssertionError('unsupported')


def cpu_oracle(functions, iterations=96):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ProofError('private direct-CPU verification requires Linux x86-64')
    test_values=[0,1,2,0xffffffff,0x100000000,0x7fffffffffffffff,
                 0x8000000000000000,0xffffffffffffffff]
    rng=random.Random(189)
    test_values += [rng.getrandbits(64) for _ in range(iterations)]
    verified=0
    for kind, (address, size, imm, code) in zip(PATTERNS,functions):
        if size != len(code) or identify(code)!=(kind,size,imm):
            raise ProofError('oracle bytes no longer match supported grammar')
        # W^X: write a fresh anonymous page, then revoke write permission
        # BEFORE executing the strictly verified original scalar code.
        with mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE) as mem:
            mem[:len(code)]=code
            pointer=ctypes.addressof(ctypes.c_char.from_buffer(mem))
            libc=ctypes.CDLL(None)
            libc.mprotect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
            libc.mprotect.restype=ctypes.c_int
            if libc.mprotect(pointer,4096,mmap.PROT_READ|mmap.PROT_EXEC)!=0:
                raise ProofError('could not enforce RX for private CPU oracle')
            fn=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_uint64)(pointer)
            for value in test_values:
                if fn(value)!=expected(kind,value,imm):
                    raise ProofError('actual CPU scalar result disagrees with decoded semantics')
                verified+=1
    return verified


def emit_private_c(out: Path, functions):
    if out.is_symlink() or not out.is_dir() or any(out.iterdir()):
        raise ProofError('generated private C output must be an empty regular directory')
    cmain=['/* PRIVATE generated data from locally owned Bloodborne. NO REDISTRIBUTION. */',
           '#include "recomp_abi.h"',
           *[f'extern void game_leaf_{i}(BbCpu *cpu);' for i in range(len(functions))],
           *[f'static RcFn direct_{i} = game_leaf_{i};' for i in range(len(functions))],
           'static const RcFunction table[] = {',
           *[f'{{{addr}, {size}, 0, game_leaf_{i}, &direct_{i}}},'
             for i,(addr,size,imm,_) in enumerate(functions)],
           '};',
           '__attribute__((visibility("default"))) const RcFunction *bb_recomp_init(const RcApi *api,size_t *count) {',
           '  if(!api || !count || api->version != BB_RECOMP_API_VERSION) return 0;',
           '  *count=sizeof(table)/sizeof(table[0]); return table;',
           '}']
    leaf=['/* PRIVATE game-derived scalar AOT; a bounded leaf-only proof, not entire engine. */',
          '#include "recomp_abi.h"','struct BbCpu { uint64_t r[16]; uint64_t rip; };']
    for i, (kind, (addr,size,imm,code)) in enumerate(zip(PATTERNS,functions)):
        if kind=='zero32':expr='0ull'
        elif kind=='imm32':expr=str(imm)+'ull'
        elif kind=='identity64':expr='cpu->r[7]'
        elif kind=='identity32':expr='(uint32_t)cpu->r[7]'
        else:raise ProofError('unsupported leaf kind')
        leaf += [f'void game_leaf_{i}(BbCpu *cpu) {{ cpu->r[0] = {expr}; }}']
    (out/'recomp.c').write_text('\n'.join(cmain)+'\n',encoding='utf-8')
    (out/'recomp_1.c').write_text('\n'.join(leaf)+'\n',encoding='utf-8')


def abi_dir() -> Path:
    here = Path(__file__).resolve().parent
    # Standalone local research archive or stacked GitHub v187 module.
    for p in (here/'abi', here.parent/'recomp-v187'):
        if (p/'recomp_abi.h').is_file():
            return p
    raise ProofError('pinned public v187 ABI header unavailable')


def probe_compiled_library(path: Path, functions):
    """Call the leaf functions through the v4 C ABI in the host process."""
    library=ctypes.CDLL(str(path))
    class Cpu(ctypes.Structure):_fields_=[('r',ctypes.c_uint64*16),('rip',ctypes.c_uint64)]
    class Function(ctypes.Structure):_fields_=[('offset',ctypes.c_uint64),('size',ctypes.c_uint64),('hash',ctypes.c_uint64),('fn',ctypes.c_void_p),('direct',ctypes.c_void_p)]
    class Api(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('image_base',ctypes.c_uint64),('step',ctypes.c_void_p),('call',ctypes.c_void_p),('tail',ctypes.c_void_p),('bail',ctypes.c_void_p),('trace',ctypes.c_void_p)]
    entry=library.bb_recomp_init
    entry.argtypes=[ctypes.POINTER(Api),ctypes.POINTER(ctypes.c_size_t)]
    entry.restype=ctypes.POINTER(Function)
    count=ctypes.c_size_t()
    arr=entry(ctypes.byref(Api(version=4)),ctypes.byref(count))
    if not arr or count.value!=len(functions):
        raise ProofError('generated module init ABI mismatch')
    values=[0,1,0xffffffff,0x100000000,0xffffffffffffffff]
    values += [random.Random(189+i).getrandbits(64) for i in range(64)]
    verified=0
    for i,(kind,(address,size,imm,_)) in enumerate(zip(PATTERNS,functions)):
        desc=arr[i]
        if desc.offset!=address or desc.size!=size or not desc.fn:
            raise ProofError('recompiled leaf descriptor mismatch')
        compiled=ctypes.CFUNCTYPE(None,ctypes.POINTER(Cpu))(desc.fn)
        for x in values:
            cpu=Cpu();cpu.r[7]=x
            compiled(ctypes.byref(cpu))
            if cpu.r[0]!=expected(kind,x,imm):
                raise ProofError('compiled scalar game semantics mismatch')
            verified+=1
    return verified


def check_linux_generated(out: Path, functions):
    so=out.parent/'private_leaf_test.so'
    cmd=['clang','-shared','-fPIC','-nostdlib','-Werror','-O2',
         '-I'+str(abi_dir()),
         str(out/'recomp.c'),str(out/'recomp_1.c'),'-o',str(so)]
    r=subprocess.run(cmd,capture_output=True,timeout=40)
    if r.returncode:
        raise ProofError('private generated C failed native Linux compilation')
    return probe_compiled_library(so, functions)


def main():
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--eboot',type=Path,required=True)
    p.add_argument('--private-output-dir',type=Path,required=True)
    p.add_argument('--skip-cpu-oracle',action='store_true')
    a=p.parse_args()
    try:
        image,starts=load_original(a.eboot)
        game=select(image,starts)
        cpu=0 if a.skip_cpu_oracle else cpu_oracle(game)
        emit_private_c(a.private_output_dir,game)
        compiled=check_linux_generated(a.private_output_dir,game)
        print(json.dumps({'status':'pass','actual_private_game_image_verified':True,
             'source_code_is_real_game_derived':True,
             'functions_compiled_from_real_private_game':len(game),
             'cpu_oracle_matches':cpu,'native_linux_compiled_matches':compiled,
             'win64_dll_built':False,'ps4_free_game_boot_proven':False},separators=(',',':')))
        return 0
    except (ProofError,OSError,struct.error,subprocess.TimeoutExpired) as err:
        print(json.dumps({'status':'fail','reason':str(err) if isinstance(err,ProofError) else 'private source error'}))
        return 2

if __name__=='__main__':sys.exit(main())
