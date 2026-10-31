#!/usr/bin/env python3
"""V192: narrowly verified REAL user-owned 1.09 call-pair recompile proof.

Read-only, source-hash-locked ELF intake. Generated game-derived C and binaries
are private, never emitted to stdout, GitHub Actions or public repositories.
Only two exact small call-site grammars and two exact leaf templates are allowed.
The original CPU oracle relocates *only* CALL rel32, preserving source semantics.
Not a full recompiler or game runtime.
"""
from __future__ import annotations
import argparse
import ctypes
import importlib.util
import json
import mmap
from pathlib import Path
import platform
import random
import struct
import subprocess
import sys

HERE=Path(__file__).resolve().parent

def load_module(name: str, paths):
    for path in paths:
        if path.is_file() and not path.is_symlink():
            spec=importlib.util.spec_from_file_location(name,path)
            obj=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(obj)
            return obj
    raise RuntimeError('expected pinned local source-port module missing')

v191=load_module('v191_call_base',[HERE.parent/'recomp-v191'/'branch_cfg_v191.py',HERE.parent/'native_real_branch_v191'/'branch_cfg_v191.py'])
v190=v191.v190
v189=v191.v189

class PairError(ValueError):pass
DEF_FLAGS=0x8c5
FRAME_SIZES=(16,32,48)
MAX_ROWS=3
VALUES=[0,1,2,3,7,17,127,255,256,0x7fffffff,0x80000000,0xffffffff,0x100000000,0x8000000000000000,0xffffffffffffffff]+[random.Random(192+i).getrandbits(64) for i in range(57)]

def valid_alignment_nop(rest:bytes)->bool:
    # Re-accept the 9-byte CS-prefixed Intel multi-NOP with 0..6 0x66
    # prefixes. clang regularly pads true 16/32-byte FDE boundaries with it.
    # Reject arbitrary mixed or hidden instructions, no permissive trailing bytes.
    if v190.valid_nops(rest):return True
    base=b'\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00'
    return any(rest==b'\x66'*i+base for i in range(7))


def parse_caller(code: bytes):
    """Call graph is a verified ELF direct FDE -> FDE edge, not guessed.

    Grammar A: push rbp; mov rbp,rsp; call rel32; add rax,imm32; pop rbp; ret
    Grammar B: push rbp; mov rbp,rsp; call rel32; mov ecx,eax; sar ecx,31;
               and ecx,eax; mov eax,ecx; pop rbp; ret.
    Strict first-ret and exact NOP tail. No other indirect control transfers.
    """
    if len(code) not in (32,48) or not code.startswith(b'\x55\x48\x89\xe5\xe8'):
        raise PairError('unsupported game stack/call prologue')
    rel=struct.unpack_from('<i',code,5)[0]
    if code[9:11]==b'\x48\x05' and len(code)>=17 and code[15:17]==b'\x5d\xc3':
        kind='call-add64';extra=struct.unpack_from('<I',code,11)[0];end=17
    elif code[9:20]==b'\x89\xc1\xc1\xf9\x1f\x21\xc1\x89\xc8\x5d\xc3':
        kind='call-mask32';extra=0;end=20
    else:raise PairError('unrecognized post-CALL or stack epilogue')
    if not valid_alignment_nop(code[end:]):
        raise PairError('noncanonical tail after original stack epilogue')
    return kind,extra,rel,end

def parse_target(code:bytes):
    """Only a complete original real game leaf, not a guessed callee/PLT."""
    if len(code)!=16:raise PairError('callee frame size mismatch')
    identified=v189.identify(code)
    if identified is None or identified[0] not in ('zero32','imm32'):
        raise PairError('unverified real direct-call target')
    kind,length,imm=identified
    if not valid_alignment_nop(code[length:]):raise PairError('unexpected bytes following callee RET')
    return kind,imm

def bind_pair(image:bytes,starts:list[int],a:int,b:int):
    # Bind full exact EH-frame original source+target; no arbitrary offsets.
    offsets={x:i for i,x in enumerate(starts)}
    if a not in offsets or b not in offsets:
        raise PairError('source or target is not an exact original FDE start')
    ia,ib=offsets[a],offsets[b]
    if ia+1>=len(starts) or ib+1>=len(starts):raise PairError('missing FDE boundary')
    ea,eb=starts[ia+1],starts[ib+1]
    if not (0<=a<ea<=len(image) and 0<=b<eb<=len(image)):
        raise PairError('image boundary mismatch')
    caller=bytes(image[a:ea]);target=bytes(image[b:eb])
    kind,extra,rel,end=parse_caller(caller)
    callee_kind,imm=parse_target(target)
    if a+9+rel != b:
        raise PairError('original ELF CALL relative displacement resolves elsewhere')
    if kind=='call-add64' and callee_kind!='imm32':
        raise PairError('add64 caller expected an immediate-return leaf')
    if kind=='call-mask32' and callee_kind!='zero32':
        raise PairError('mask32 caller expected a zero-return leaf')
    return {'start':a,'target':b,'caller':caller,'callee':target,'kind':kind,'imm':imm,'extra':extra}

def select(image:bytes,starts:list[int],limit:int=MAX_ROWS):
    if limit!=MAX_ROWS or len(starts)>v189.MAX_FDE:
        raise PairError('unexpected real game sample limits')
    offsets={a:i for i,a in enumerate(starts)}
    rows=[];kinds={'call-add64':0,'call-mask32':0}
    for a,end in zip(starts,starts[1:]):
        if end-a not in (32,48):continue
        try:
            kind,extra,rel,_=parse_caller(bytes(image[a:end]))
            b=a+9+rel
            if b not in offsets:continue
            item=bind_pair(image,starts,a,b)
        except PairError:continue
        if kinds[kind] >= (1 if kind=='call-add64' else 2):continue
        rows.append(item);kinds[kind]+=1
        if len(rows)==limit:break
    if kinds!={'call-add64':1,'call-mask32':2}:
        raise PairError('expected verified original game caller/callee classes missing')
    return rows

def expected(row:dict):
    if row['kind']=='call-add64':
        a=row['imm'];b=row['extra'];result=(a+b)&0xffffffffffffffff
        carry=int(result<a)
        overflow=int((~(a^b)&(a^result)&(1<<63))!=0)
        flags=(carry | (overflow<<11) | (0x40 if result==0 else 0) |
               (0x80 if result&(1<<63) else 0) |
               (4 if (result&255).bit_count()%2==0 else 0))
        return result, flags
    if row['kind']=='call-mask32':
        result=0
        return result,0x44 # AND on zero -> PF/ZF, no CF/OF
    raise PairError('unexpected selected call type')

def _linked_page(row:dict):
    """Only CALL displacement is relocated; caller/callee bytes remain original.

    +0x100: original caller with rel32 replaced to land in +0x200 callee.
    +0x200: original callee. +0: generic instrumented flags wrapper.
    The source target MUST be an exact FDE-verified game instruction stream.
    """
    parse_caller(row['caller']);parse_target(row['callee'])
    original=int.from_bytes(row['caller'][5:9],'little',signed=True)
    if row['start']+9+original != row['target']:
        raise PairError('cannot relocate altered game callsite')
    mem=mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE)
    caller=bytearray(row['caller']);caller[5:9]=struct.pack('<i',0x200-(0x100+9))
    mem[0x100:0x100+len(caller)]=caller
    mem[0x200:0x200+len(row['callee'])]=row['callee']
    # Wrapper: sub rsp,8; call +0x100; pushfq; pop rax; add rsp,8; ret.
    # Actual caller still push rbp -> call callee -> pop rbp -> ret, preserving stack.
    wrapper=b'\x48\x83\xec\x08'+b'\xe8'+struct.pack('<i',0x100-9)+b'\x9c\x58\x48\x83\xc4\x08\xc3'
    mem[:len(wrapper)]=wrapper
    ptr=ctypes.addressof(ctypes.c_char.from_buffer(mem))
    libc=ctypes.CDLL(None)
    libc.mprotect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
    libc.mprotect.restype=ctypes.c_int
    if libc.mprotect(ptr,4096,mmap.PROT_READ|mmap.PROT_EXEC)!=0:
        mem.close();raise PairError('failed to enforce RX/W^X on verified pair')
    return mem,ptr

def cpu_oracle(rows):
    if platform.system()!='Linux' or platform.machine()!='x86_64':
        raise PairError('private original CPU call verifier Linux/x86-64 only')
    count=0
    for row in rows:
        page,ptr=_linked_page(row)
        try:
            original=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_uint64)(ptr+0x100)
            flags_get=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_uint64)(ptr)
            want,flag_bits=expected(row)
            for val in VALUES:
                got=original(val)
                flags=flags_get(val)
                if got!=want or (flags&DEF_FLAGS)!=(flag_bits&DEF_FLAGS):
                    raise PairError('actual PS4 game CPU caller/callee AOT mismatch')
                count+=1
        finally:page.close()
    return count

def emit_private(root:Path,rows:list[dict]):
    if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
        raise PairError('private generated source must use a new empty directory')
    if not 1<=len(rows)<=MAX_ROWS:
        raise PairError('bounded game source sample count required')
    for row in rows:
        if row['start'] == row['target']:raise PairError('recursive calls unsupported')
        if row['start']+9+int.from_bytes(row['caller'][5:9],'little',signed=True)!=row['target']:
            raise PairError('unverified caller/target pair')
        parse_caller(row['caller']);parse_target(row['callee'])
    table=['/* PRIVATE USER GAME-GENERATED C. DO NOT PUBLISH. */', '#include "recomp_abi.h"',
           *[f'extern void game_caller_{i}(BbCpu*);' for i in range(len(rows))],
           *[f'static RcFn direct_{i}=game_caller_{i};' for i in range(len(rows))],
           'static const RcFunction table[]={',
           *[f'{{{r["start"]}ull,{len(r["caller"])}ull,0,game_caller_{i},&direct_{i}}},' for i,r in enumerate(rows)],
           '};',
           '__attribute__((visibility("default"))) const RcFunction *bb_recomp_init(const RcApi *api,size_t *count){',
           ' if(!api||!count||api->version!=BB_RECOMP_API_VERSION)return 0;',
           ' *count=sizeof(table)/sizeof(table[0]);return table;','}']
    source=['/* PRIVATE USER GAME-GENERATED C. NOT THE FULL GAME ENGINE. */',
            '#include "recomp_abi.h"','#include <stdint.h>',
            '#include <stddef.h>',
            'struct BbCpu { uint64_t r[16]; uint64_t rip; uint64_t flags; };',
            '_Static_assert(offsetof(struct BbCpu,r)==0 && offsetof(struct BbCpu,rip)==128 && offsetof(struct BbCpu,flags)==136,"upstream prefix");',
            'static uint64_t fp(uint64_t x){return ((x&255u) && __builtin_parity((unsigned)(x&255u)) ? 0ull : 4ull) | ((x&255u)==0?4ull:0ull);}',
            ]
    # The exact native C CALL is direct, not a synthetic PS4-compatible thunk.
    for i,row in enumerate(rows):
        if row['kind']=='call-add64':
            source += [f'__attribute__((noinline)) static void game_callee_{i}(BbCpu *c){{ c->r[0]={row["imm"]}ull; }}',
                       f'void game_caller_{i}(BbCpu *c){{',
                       f' game_callee_{i}(c); uint64_t a=c->r[0],b={row["extra"]}ull, r=a+b;',
                       ' uint64_t ov=((~(a^b)&(a^r))>>63)&1ull;',
                       ' uint64_t bits=((r<a)?1ull:0ull)|(ov<<11)|(r==0?0x40ull:0ull)|((r>>56)&0x80ull)|fp(r);',
                       ' c->r[0]=r; c->flags=(c->flags&~0x8c5ull)|bits;',
                       '}']
        else:
            source += [f'__attribute__((noinline)) static void game_callee_{i}(BbCpu *c){{ c->r[0]=0; c->flags=(c->flags&~0x8c5ull)|0x44ull; }}',
                       f'void game_caller_{i}(BbCpu *c){{',
                       f' game_callee_{i}(c); uint32_t v=(uint32_t)c->r[0];',
                       ' uint32_t sign=(v&0x80000000u)?0xffffffffu:0u;',
                       ' v &= sign; c->r[0]=v;',
                       ' uint64_t bits=(v==0?0x40ull:0ull)|((v&0x80000000u)?0x80ull:0ull)|fp(v);',
                       ' c->flags=(c->flags&~0x8c5ull)|bits;',
                       '}']
    (root/'recomp.c').write_text('\n'.join(table)+'\n',encoding='utf-8')
    (root/'recomp_1.c').write_text('\n'.join(source)+'\n',encoding='utf-8')

def probe_compiled(lib:Path,rows:list[dict]):
    library=ctypes.CDLL(str(lib))
    try:
        class Cpu(ctypes.Structure):_fields_=[('r',ctypes.c_uint64*16),('rip',ctypes.c_uint64),('flags',ctypes.c_uint64)]
        class Func(ctypes.Structure):_fields_=[('offset',ctypes.c_uint64),('size',ctypes.c_uint64),('hash',ctypes.c_uint64),('fn',ctypes.c_void_p),('direct',ctypes.c_void_p)]
        class Api(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('image_base',ctypes.c_uint64),('step',ctypes.c_void_p),('call',ctypes.c_void_p),('tail',ctypes.c_void_p),('bail',ctypes.c_void_p),('trace',ctypes.c_void_p)]
        fn=library.bb_recomp_init
        fn.argtypes=[ctypes.POINTER(Api),ctypes.POINTER(ctypes.c_size_t)]
        fn.restype=ctypes.POINTER(Func)
        count=ctypes.c_size_t()
        table=fn(ctypes.byref(Api(version=4)),ctypes.byref(count))
        if not table or count.value != len(rows):raise PairError('native Win64 ABI function table mismatch')
        done=0
        for i,row in enumerate(rows):
            if table[i].offset!=row['start'] or table[i].size!=len(row['caller']) or not table[i].fn:
                raise PairError('compiled interprocedural function descriptor drift')
            method=ctypes.CFUNCTYPE(None,ctypes.POINTER(Cpu))(table[i].fn)
            want,flags=expected(row)
            for value in VALUES:
                cpu=Cpu();cpu.r[7]=value;cpu.r[0]=0xdeadbeef00112233;cpu.flags=0x123456789abcdef0
                method(ctypes.byref(cpu))
                if cpu.r[0]!=want or (cpu.flags&DEF_FLAGS)!=(flags&DEF_FLAGS):
                    raise PairError('native C game CALL graph differs from original CPU')
                done+=1
        return done
    finally:
        if sys.platform=='win32':
            import _ctypes
            _ctypes.FreeLibrary(library._handle)
            library._handle=0

def compile_linux(root:Path,rows):
    lib=root.parent/'private_v192_game_call.so'
    cmd=['clang','-std=c11','-O2','-fPIC','-shared','-I',str(v189.abi_dir()),str(root/'recomp.c'),str(root/'recomp_1.c'),'-o',str(lib)]
    try:r=subprocess.run(cmd,capture_output=True,timeout=90)
    except (OSError,subprocess.TimeoutExpired) as e:raise PairError('native compiler unavailable') from e
    if r.returncode:raise PairError('native C source cannot be compiled, inspect privately')
    return probe_compiled(lib,rows)

def cli():
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--eboot',type=Path,required=True)
    p.add_argument('--private-output-dir',type=Path,required=True)
    args=p.parse_args()
    try:
        img,starts=v189.load_original(args.eboot)
        rows=select(img,starts)
        original=cpu_oracle(rows)
        emit_private(args.private_output_dir,rows)
        compiled=compile_linux(args.private_output_dir,rows)
    except (PairError,v189.ProofError, OSError):
        print('V192_PRIVATE_GAME_CALL_SAFE_REJECTION',file=sys.stderr)
        return 2
    print(json.dumps({'stage':'v192','user_private_loaded_image_verified':True,
                      'actual_game_direct_call_pairs':len(rows),
                      'original_relocated_call_cpu_checks':original,
                      'native_compiled_game_call_checks':compiled,
                      'generated_windows_game_dll_executed':False,
                      'game_boot_or_online_verified':False},separators=(',',':')))
    return 0
if __name__=='__main__':raise SystemExit(cli())
