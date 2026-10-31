#!/usr/bin/env python3
"""V190: bounded private 1.09 game scalar/memory/SSE leaf AOT, not a game port.

Only a strict subset of 16-byte original FDE functions may be selected. Raw game
bytes and generated C remain LOCAL. Never publish the private output directory.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import importlib.util
import json
import mmap
from pathlib import Path
import platform
import random
import struct
import subprocess
import sys

V189_DIR = Path(__file__).resolve().parent.parent / 'recomp-v189'
# A research checkout may use a local adjacent v189 directory.
if not (V189_DIR / 'real_leaf_recomp_v189.py').is_file():
    V189_DIR = Path(__file__).resolve().parent.parent / 'native_real_leaf_v189'
if not (V189_DIR / 'real_leaf_recomp_v189.py').is_file():
    raise RuntimeError('required pinned V189 verifier unavailable')
spec=importlib.util.spec_from_file_location('v189_base',V189_DIR/'real_leaf_recomp_v189.py')
v189=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v189)

KINDS=('mem64','mem32','store64','lea64','sse32','flags_eq32')
MAX_OFFSET=112
SAMPLES=64
# 16-byte LLVM-style alignment padding, parsed as explicit safe NOP blocks.
NOP_BYTES=tuple(bytes.fromhex(x) for x in (
    '90','6690','0f1f00','0f1f4000','0f1f440000','660f1f440000',
    '0f1f8000000000','0f1f840000000000','660f1f840000000000',
    '2e0f1f840000000000','662e0f1f840000000000',
    '66662e0f1f840000000000','6666662e0f1f840000000000'
))

class GateError(ValueError): pass


def valid_nops(rest:bytes)->bool:
    if not rest:return True
    # No arbitrary 0x66 padding, which could mask actual instructions.
    reachable=[False]*(len(rest)+1)
    reachable[0]=True
    for i in range(len(rest)):
        if not reachable[i]:continue
        for v in NOP_BYTES:
            if rest.startswith(v,i):reachable[i+len(v)]=True
    return reachable[-1]


def decode(code: bytes):
    """(kind,instruction_bytes,offset): byte-exact RDI/RDI+disp, no branches/calls.

    Return immediately at the selected instruction size. Reject all other
    addressing modes, segment overrides, negative/large offsets and suffixes.
    """
    forms=[
      ('mem64', b'\x48\x8b\x47',5,3,8),
      ('mem32', b'\x8b\x47',4,2,4),
      ('store64', b'\x48\x89\x77',5,3,8),
      ('lea64', b'\x48\x8d\x47',5,3,0),
      ('sse32', b'\xc5\xfa\x10\x47',6,4,4),
    ]
    for kind,prefix,n,at,size in forms:
        if len(code)>=n and code.startswith(prefix) and code[n-1]==0xc3:
            offset=int.from_bytes(code[at:at+1], 'little', signed=True)
            if offset<0 or offset+size>128 or offset>MAX_OFFSET:
                return None
            return (kind,n,offset) if valid_nops(code[n:]) else None
    if code.startswith(b'\x85\xff\x0f\x94\xc0\xc3') and valid_nops(code[6:]):
        # test edi,edi ; sete al ; ret. CF=OF=0; ZF,PF,SF defined.
        return 'flags_eq32',6,0
    return None


def select(image:bytes,starts:list[int]):
    found={}
    for a,b in zip(starts,starts[1:]):
        if b-a!=16 or a<0 or b>len(image):continue
        match=decode(image[a:b])
        if match is None:continue
        kind,size,off=match
        if kind not in found:
            found[kind]={'kind':kind,'start':a,'size':size,'offset':off,'code':bytes(image[a:a+size])}
        if len(found)==len(KINDS):break
    missing=set(KINDS)-set(found)
    if missing:raise GateError('unavailable strict native function classes: '+','.join(sorted(missing)))
    return [found[x] for x in KINDS]


def sample_values():
    rng=random.Random(190)
    return [0,1,2,3,0x7fffffff,0x80000000,0xffffffff,
            0x100000000,0x8000000000000000,0xffffffffffffffff] + [rng.getrandbits(64) for _ in range(SAMPLES)]


def _rx_function(code:bytes):
    """Return (memory, fnptr) with Linux W^X only; caller holds mapping alive."""
    if platform.system()!='Linux' or platform.machine()!='x86_64':
        raise GateError('original byte CPU oracle available only on Linux x86-64')
    mem=mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE)
    mem[:len(code)]=code
    ptr=ctypes.addressof(ctypes.c_char.from_buffer(mem))
    libc=ctypes.CDLL(None)
    libc.mprotect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
    libc.mprotect.restype=ctypes.c_int
    if libc.mprotect(ptr,4096,mmap.PROT_READ|mmap.PROT_EXEC)!=0:
        mem.close();raise GateError('unable to enforce RX before game function call')
    return mem,ptr


def _flags_wrapper(code:bytes):
    """Absolute-free x86-64 wrapper: call strict function, pushfq;pop rax.

    Wrapper bytes are generic testing infrastructure, not game content.
    It must capture flags BEFORE any ALU instruction after the original RET.
    """
    # call rel32 to function at +0x80; at entry stack ABI alignment is 8.
    prolog=b'\x48\x83\xec\x08' # sub rsp,8, align for nested call
    call=b'\xe8'+struct.pack('<i',0x80-(len(prolog)+5))
    epilog=b'\x9c\x58\x48\x83\xc4\x08\xc3'
    page=prolog+call+epilog
    return page+b'\x90'*(0x80-len(page))+code


def cpu_oracle(rows,iterations=24):
    verified=0
    vals=sample_values()[:10+iterations]
    for row in rows:
        kind,code,off=row['kind'],row['code'],row['offset']
        if decode(code)!=(kind,len(code),off):
            raise GateError('selected private code failed strict whitelist recheck')
        page,ptr=_rx_function(code)
        try:
            if kind=='flags_eq32':
                with mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE) as wrapper:
                    w=_flags_wrapper(code)
                    wrapper[:len(w)]=w
                    wrapperptr=ctypes.addressof(ctypes.c_char.from_buffer(wrapper))
                    libc=ctypes.CDLL(None)
                    libc.mprotect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
                    libc.mprotect.restype=ctypes.c_int
                    if libc.mprotect(wrapperptr,4096,mmap.PROT_READ|mmap.PROT_EXEC)!=0:
                        raise GateError('RX flags wrapper failed')
                    fn=ctypes.CFUNCTYPE(ctypes.c_uint8,ctypes.c_uint64)(ptr)
                    getflags=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_uint64)(wrapperptr)
                    for val in vals:
                        edi=val & 0xffffffff
                        if fn(val)!=(edi==0): raise GateError('real CPU AL flag mismatch')
                        flags=getflags(val)
                        defined=0x8c5 # CF/PF/ZF/SF/OF
                        pf=(bin(edi&255).count('1')%2==0)
                        expect=(0x40 if edi==0 else 0) | (0x80 if edi&0x80000000 else 0) | (0x4 if pf else 0)
                        if (flags&defined)!=(expect&defined): raise GateError('real CPU RFLAGS mismatch')
                        verified+=1
            elif kind=='store64':
                fn=ctypes.CFUNCTYPE(None,ctypes.c_void_p,ctypes.c_uint64)(ptr)
                for val in vals:
                    mem=(ctypes.c_ubyte*160)(*([0xa5]*160))
                    p=ctypes.addressof(mem)
                    fn(p,val)
                    expected=bytearray([0xa5]*160)
                    expected[off:off+8]=struct.pack('<Q',val)
                    if bytes(mem)!=bytes(expected):raise GateError('real CPU memory write mismatch')
                    verified+=1
            elif kind=='sse32':
                fn=ctypes.CFUNCTYPE(ctypes.c_float,ctypes.c_void_p)(ptr)
                for val in vals:
                    raw=(val & 0x7f7fffff) # only non-NaN finite f32
                    mem=(ctypes.c_ubyte*160)(*([0x35]*160))
                    p=ctypes.addressof(mem)
                    ctypes.memmove(p+off,struct.pack('<I',raw),4)
                    actual=struct.unpack('<I',struct.pack('<f',fn(p)))[0]
                    if actual!=raw:raise GateError('real CPU scalar SSE load mismatch')
                    verified+=1
            else:
                fn=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_uint64)(ptr)
                for val in vals:
                    if kind.startswith('mem'):
                        mem=(ctypes.c_ubyte*160)(*([0x57]*160))
                        p=ctypes.addressof(mem)
                        n=8 if kind=='mem64' else 4
                        ctypes.memmove(p+off,struct.pack('<Q',val)[:n],n)
                        got=fn(p)
                        want=val & (0xffffffffffffffff if n==8 else 0xffffffff)
                    elif kind=='lea64':
                        got=fn(val)
                        want=(val+off)&0xffffffffffffffff
                    else:raise GateError('unexpected')
                    if got!=want:raise GateError('real CPU pointer or scalar mismatch')
                    verified+=1
        finally:page.close()
    return verified


def emit(out:Path,rows):
    if out.is_symlink() or not out.is_dir() or any(out.iterdir()):
        raise GateError('private output must be a newly created empty directory')
    if [r['kind'] for r in rows]!=list(KINDS):raise GateError('incomplete function classes')
    # This is a small synthetic CPU layout; no claim of full upstream BbCpu ABI.
    lines=['/* USER-PRIVATE GENERATED FROM GAME; NEVER PUBLISH */', '#include "recomp_abi.h"',
           '#include <stdint.h>', '#include <stddef.h>',
           'union V { unsigned char b[32]; float f[8]; };',
           'struct BbCpu { uint64_t r[16]; uint64_t rip; uint64_t flags; union V v[16]; };',
           '_Static_assert(offsetof(struct BbCpu,v)==144,"v190 mock layout");']
    for i,r in enumerate(rows):
        kind,off=r['kind'],r['offset']
        if kind=='mem64': expr=f'uint64_t v; __builtin_memcpy(&v,(const void*)(uintptr_t)(cpu->r[7]+{off}),8); cpu->r[0]=v;'
        elif kind=='mem32':expr=f'uint32_t v; __builtin_memcpy(&v,(const void*)(uintptr_t)(cpu->r[7]+{off}),4); cpu->r[0]=v;'
        elif kind=='store64':expr=f'__builtin_memcpy((void*)(uintptr_t)(cpu->r[7]+{off}),&cpu->r[6],8);'
        elif kind=='lea64':expr=f'cpu->r[0]=cpu->r[7]+{off}ull;'
        elif kind=='sse32':expr=f'__builtin_memset(cpu->v[0].b,0,32); __builtin_memcpy(cpu->v[0].b,(const void*)(uintptr_t)(cpu->r[7]+{off}),4);'
        elif kind=='flags_eq32':expr='uint32_t x=(uint32_t)cpu->r[7]; unsigned pf=__builtin_parity((unsigned)(x&255))==0; cpu->flags=(cpu->flags&~0x8c5ull)|(x==0?0x40ull:0ull)|(x&0x80000000u?0x80ull:0ull)|(pf?0x4ull:0ull); cpu->r[0]=(cpu->r[0]&~255ull)|(x==0);'
        else: raise GateError('unsupported')
        lines.append(f'void native_leaf_{i}(BbCpu *cpu) {{ {expr} }}')
    cmain=['/* USER-PRIVATE original game references; never redistribute */','#include "recomp_abi.h"',
           *[f'extern void native_leaf_{i}(BbCpu *cpu);' for i in range(len(rows))],
           *[f'static RcFn direct_{i}=native_leaf_{i};' for i in range(len(rows))],
           'static const RcFunction table[] = {',
           *[f'{{{r["start"]}ull,{r["size"]}ull,0,native_leaf_{i},&direct_{i}}},' for i,r in enumerate(rows)],
           '};','__attribute__((visibility("default"))) const RcFunction *bb_recomp_init(const RcApi *api,size_t *count) {',
           'if (!api||!count||api->version!=BB_RECOMP_API_VERSION) return 0;',
           '*count=sizeof(table)/sizeof(table[0]); return table;','}']
    (out/'recomp.c').write_text('\n'.join(cmain)+'\n',encoding='utf-8')
    (out/'recomp_1.c').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def compile_probe(out:Path,rows):
    """Only native local Linux shared library; never uploaded to CI."""
    compiler='clang'
    header=v189.abi_dir()
    so=out/'private_nontrivial.so'
    cmd=[compiler,'-std=c11','-O2','-fPIC','-shared','-I',str(header),str(out/'recomp.c'),str(out/'recomp_1.c'),'-o',str(so)]
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    except (OSError,subprocess.TimeoutExpired) as e:raise GateError('local C compiler unavailable or timed out') from e
    if p.returncode:raise GateError('native C compiler rejected private translation')
    return probe_compiled_library(so,rows)


def probe_compiled_library(so:Path,rows):
    """Native callback verification, incl. explicit unload on Windows."""
    lib=ctypes.CDLL(str(so))
    try:
        class V(ctypes.Union):_fields_=[('b',ctypes.c_ubyte*32),('f',ctypes.c_float*8)]
        class Cpu(ctypes.Structure):_fields_=[('r',ctypes.c_uint64*16),('rip',ctypes.c_uint64),('flags',ctypes.c_uint64),('v',V*16)]
        class Fn(ctypes.Structure):_fields_=[('offset',ctypes.c_uint64),('size',ctypes.c_uint64),('hash',ctypes.c_uint64),('fn',ctypes.c_void_p),('direct',ctypes.c_void_p)]
        class Api(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('image_base',ctypes.c_uint64),('step',ctypes.c_void_p),('call',ctypes.c_void_p),('tail',ctypes.c_void_p),('bail',ctypes.c_void_p),('trace',ctypes.c_void_p)]
        init=lib.bb_recomp_init
        init.restype=ctypes.POINTER(Fn)
        init.argtypes=[ctypes.POINTER(Api),ctypes.POINTER(ctypes.c_size_t)]
        api=Api();api.version=4;count=ctypes.c_size_t()
        fs=init(ctypes.byref(api),ctypes.byref(count))
        if count.value!=len(rows):raise GateError('native compiled function count mismatch')
        vals=sample_values()
        tests=0
        for i,r in enumerate(rows):
            if fs[i].offset!=r['start'] or fs[i].size!=r['size']:
                raise GateError('private source function table corrupted')
            func=ctypes.CFUNCTYPE(None,ctypes.POINTER(Cpu))(fs[i].fn)
            off=r['offset'];kind=r['kind']
            for val in vals:
                cpu=Cpu();cpu.r[0]=0xdeafbeef12345678;cpu.r[6]=val;cpu.flags=0xfedcaf9876543210
                buf=(ctypes.c_ubyte*160)(*([0xa5]*160))
                p=ctypes.addressof(buf)
                cpu.r[7]=val if kind in ('lea64','flags_eq32') else p
                if kind in ('mem64','mem32'):
                    n=8 if kind=='mem64' else 4
                    ctypes.memmove(p+off,struct.pack('<Q',val)[:n],n)
                elif kind=='sse32':
                    ctypes.memmove(p+off,struct.pack('<I',val & 0x7f7fffff),4)
                func(ctypes.byref(cpu))
                if kind=='mem64':good=cpu.r[0]==val
                elif kind=='mem32':good=cpu.r[0]==(val&0xffffffff)
                elif kind=='store64':
                    good=(bytes(buf[:off])==bytes([0xa5]*off) and bytes(buf[off:off+8])==struct.pack('<Q',val) and bytes(buf[off+8:])==bytes([0xa5]*(160-off-8)))
                elif kind=='lea64':good=cpu.r[0]==((val+off)&0xffffffffffffffff)
                elif kind=='sse32':good=bytes(cpu.v[0].b[:4])==struct.pack('<I',val&0x7f7fffff) and bytes(cpu.v[0].b[4:])==bytes(28)
                elif kind=='flags_eq32':
                    x=val&0xffffffff
                    pf=bin(x&255).count('1')%2==0
                    want=(0x40 if x==0 else 0)|(0x80 if x&0x80000000 else 0)|(0x4 if pf else 0)
                    good=(cpu.r[0]&255)==(x==0) and cpu.r[0]&~255 == 0xdeafbeef12345600 and (cpu.flags&0x8c5)==want
                else:good=False
                if not good:raise GateError('native compiled C failed nontrivial memory/flags/SSE probe')
                tests+=1
        return tests
    finally:
        if sys.platform == 'win32':
            import _ctypes
            _ctypes.FreeLibrary(lib._handle)
            lib._handle=0
        del lib


def main():
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--eboot',type=Path,required=True)
    p.add_argument('--private-output-dir',type=Path,required=True)
    a=p.parse_args()
    image,starts=v189.load_original(a.eboot)
    rows=select(image,starts)
    count=cpu_oracle(rows)
    emit(a.private_output_dir,rows)
    compiled=compile_probe(a.private_output_dir,rows)
    # No game code, instruction bytes, private paths, FDE addresses or input data.
    print(json.dumps({'stage':'v190','game_image_sha_verified':True,'actual_game_function_kinds':len(rows),
     'original_x86_cpu_comparisons':count,'native_compiled_c_comparisons':compiled,
     'actual_Windows_DLL_game_derived_executed':False,'game_boot_or_online_verified':False},separators=(',',':')))

if __name__=='__main__':
    try:main()
    except (GateError,v189.ProofError) as e:
        print('V190_REJECTED_SAFELY',type(e).__name__,file=sys.stderr)
        raise SystemExit(2)
