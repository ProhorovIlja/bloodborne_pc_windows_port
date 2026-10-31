#!/usr/bin/env python3
"""Read-only Bloodborne 1.09 private function selection + bounded native AOT CFG proof.

No game bytes or generated C are printed or uploaded. Requires explicit, privately
owned original SCE ELF. Supports a STRICT forward-only branch / scalar subset;
unknown machine instructions and non-terminating paths always fail closed.
This is not an actual game executable or a substitute for full bb_recomp CPU ABI.
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

def _load(name, candidates):
    for source in candidates:
        if source.is_file() and not source.is_symlink():
            spec=importlib.util.spec_from_file_location(name, source)
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise RuntimeError('required local source-port validator unavailable')

v190=_load('v190_branch_base',[
    HERE.parent/'recomp-v190'/'nontrivial_leaves_v190.py',
    HERE.parent/'native_real_leaf_v190'/'nontrivial_leaves_v190.py'])
v189=v190.v189

KIND='branch-cfg'
VALID_SIZES=(16,32,48)
MAX_INS=24
MAX_FUNCTIONS=6
DEF_FLAGS=0x8c5  # x86 CF, PF, ZF, SF, OF; AF undefined for some operations
VALUES=(0,1,2,3,4,5,29,41,72,89,104,106,127,128,255,256,
        0xffffffff,0x100000000,0x7fffffff,0x80000000,0xffffffffffffffff)

class CFGError(ValueError):
    pass


def decode_one(body:bytes,pc:int):
    """Return (mnemonic, bytes, immediate/target); no arbitrary x86 decode."""
    if not 0 <= pc < len(body):
        raise CFGError('instruction outside bounded function')
    x=body[pc:]
    if x.startswith(b'\x83\xff') and len(x)>=3:
        return 'cmp-edi-i8',3,struct.unpack_from('<b',x,2)[0]
    if x.startswith(b'\x85\xff'):
        return 'test-edi',2,0
    if x.startswith(b'\x31\xc0'):
        return 'xor-eax',2,0
    if x.startswith(b'\x89\xf8'):
        return 'mov-eax-edi',2,0
    if len(x)>=5 and x[0]==0xb8:
        return 'mov-eax-i32',5,struct.unpack_from('<I',x,1)[0]
    if len(x)>=2 and x[0] in (0x74,0x75,0xeb):
        target=pc+2+struct.unpack_from('<b',x,1)[0]
        return {0x74:'je',0x75:'jne',0xeb:'jmp'}[x[0]],2,target
    if x.startswith(b'\xc3'):
        return 'ret',1,0
    raise CFGError('unsupported machine-code instruction')


def parse_cfg(body:bytes):
    """Strict forward acyclic CFG with no unparsed reachable or hidden bytes.

    Every path must write EAX before returning. Jump targets must be complete
    known instruction starts, never inside an instruction or padding. Any gap
    before the last reached byte or noncanonical padding after it fails.
    """
    if len(body) not in VALID_SIZES:
        raise CFGError('unsupported function frame size')
    pending=[(0,False)]
    ins={}
    visited=set()
    conditional=0
    while pending:
        pc,defined=pending.pop()
        if (pc,defined) in visited:
            continue
        visited.add((pc,defined))
        typ,n,arg=decode_one(body,pc)
        if pc in ins and ins[pc] != (typ,n,arg):
            raise CFGError('inconsistent instruction frontier')
        if pc not in ins and any(pc<k+width and pc+n>k for k,(_,width,_) in ins.items()):
            raise CFGError('branch enters instruction middle')
        ins[pc]=(typ,n,arg)
        if len(ins)>MAX_INS or len(visited)>2*MAX_INS:
            raise CFGError('unbounded native branch state')
        next_def=defined or typ in ('mov-eax-i32','mov-eax-edi','xor-eax')
        if typ=='ret':
            if not defined:
                raise CFGError('RAX return reads unknown incoming register')
            continue
        if typ in ('je','jne','jmp'):
            if not pc < arg < len(body):
                raise CFGError('backward, external or missing branch target')
            if typ!='jmp':
                conditional+=1
                pending.append((pc+n,next_def))
            pending.append((arg,next_def))
        else:
            pending.append((pc+n,next_def))
    if conditional<2:
        raise CFGError('not a multi-condition real CFG')
    max_end=max(k+n for k,(_,n,_) in ins.items())
    occupied=bytearray(max_end)
    for pc,(_,width,_) in ins.items():
        for j in range(pc,pc+width):
            if occupied[j]:
                raise CFGError('overlapping instructions')
            occupied[j]=1
    if not all(occupied) or not v190.valid_nops(body[max_end:]):
        raise CFGError('hidden instructions or noncanonical alignment')
    return ins


def select(image:bytes,starts:list[int],limit:int=MAX_FUNCTIONS):
    if not 1<=limit<=MAX_FUNCTIONS:
        raise CFGError('function sample outside bounded budget')
    selected=[]
    for a,b in zip(starts,starts[1:]):
        if b-a not in VALID_SIZES or not 0<=a<b<=len(image):
            continue
        try:
            frame=bytes(image[a:b]); ins=parse_cfg(frame)
        except CFGError:
            continue
        selected.append({'start':a,'size':b-a,'code':frame,'ins':ins})
        if len(selected)==limit:
            break
    if len(selected)!=limit:
        raise CFGError('insufficient original forward-branch function samples')
    return selected


def _pf(v:int)->int:
    return (int((v&0xff).bit_count()%2==0)<<2)


def _szp32(v:int):
    v &= 0xffffffff
    return (0x40 if v==0 else 0)|(0x80 if v&0x80000000 else 0)|_pf(v)


def _flags(typ:str,arg:int,edi:int,old:int)->int:
    if typ=='cmp-edi-i8':
        b=arg&0xffffffff
        result=(edi-b)&0xffffffff
        extra=(1 if edi<b else 0)| (0x800 if ((edi^b)&(edi^result)&0x80000000) else 0)
        bits=_szp32(result)|extra
    elif typ=='test-edi':
        bits=_szp32(edi)
    elif typ=='xor-eax':
        bits=0x44
    else:
        return old
    return (old&~DEF_FLAGS)|bits


def simulate(ins:dict,edi_raw:int,initial_rax:int=0xfaceb00cdeadbeef,initial_flags:int=0x123456789abcdef0):
    """Independent x86 defined-flag model for conditional path proof."""
    edi=edi_raw&0xffffffff
    acc=initial_rax
    flags=initial_flags
    pc=0
    for _ in range(MAX_INS+1):
        if pc not in ins:
            raise CFGError('path escapes validated instruction table')
        kind,length,arg=ins[pc]
        if kind=='ret':
            return acc,flags
        if kind in ('cmp-edi-i8','test-edi'):
            flags=_flags(kind,arg,edi,flags)
        elif kind=='xor-eax':
            acc=0
            flags=_flags(kind,arg,edi,flags)
        elif kind=='mov-eax-i32':
            acc=arg
        elif kind=='mov-eax-edi':
            acc=edi
        elif kind in ('je','jne','jmp'):
            take=kind=='jmp' or (bool(flags&0x40)==(kind=='je'))
            if take:
                pc=arg
                continue
        else:
            raise CFGError('unknown verified state')
        pc+=length
    raise CFGError('unexpected unbounded CFG execution')


def test_values():
    rng=random.Random(191)
    return list(VALUES)+[rng.getrandbits(64) for _ in range(96)]


def original_cpu_oracle(rows):
    """Execute ONLY exact whitelisted private game instructions, with W^X RX."""
    if platform.system()!='Linux' or platform.machine()!='x86_64':
        raise CFGError('actual private CPU oracle requires Linux x86-64')
    values=test_values()
    count=0
    for row in rows:
        code=row['code'];ins=parse_cfg(code)
        page,ptr=v190._rx_function(code)
        try:
            fn=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_uint64)(ptr)
            with mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE) as wrapper:
                w=v190._flags_wrapper(code)
                wrapper[:len(w)]=w
                wrapperptr=ctypes.addressof(ctypes.c_char.from_buffer(wrapper))
                libc=ctypes.CDLL(None)
                libc.mprotect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
                libc.mprotect.restype=ctypes.c_int
                if libc.mprotect(wrapperptr,4096,mmap.PROT_READ|mmap.PROT_EXEC)!=0:
                    raise CFGError('could not enforce RX flags wrapper')
                capture=ctypes.CFUNCTYPE(ctypes.c_uint64,ctypes.c_uint64)(wrapperptr)
                for value in values:
                    expected,flags=simulate(ins,value)
                    got=fn(value)
                    real_flags=capture(value)
                    if got!=expected or (real_flags&DEF_FLAGS)!=(flags&DEF_FLAGS):
                        raise CFGError('original CPU branch/flags differential failure')
                    count+=1
        finally:
            page.close()
    return count


def _function_c(i,row):
    lines=[f'void native_branch_{i}(BbCpu *cpu) {{',
           '  uint32_t edi = (uint32_t)cpu->r[7];',
           '  uint64_t acc = cpu->r[0], f = cpu->flags;']
    for pc,(typ,n,arg) in sorted(row['ins'].items()):
        lines.append(f' L_{pc}:;')
        if typ=='cmp-edi-i8':lines.append(f'  f=flags_cmp32(edi, (uint32_t)(int32_t){arg},f);')
        elif typ=='test-edi':lines.append('  f=flags_test32(edi,f);')
        elif typ=='xor-eax':lines.append('  acc=0; f=(f&~0x8c5ull)|0x44ull;')
        elif typ=='mov-eax-i32':lines.append(f'  acc={arg}ull;')
        elif typ=='mov-eax-edi':lines.append('  acc=edi;')
        elif typ=='je':lines.append(f'  if (f&0x40ull) goto L_{arg};')
        elif typ=='jne':lines.append(f'  if (!(f&0x40ull)) goto L_{arg};')
        elif typ=='jmp':lines.append(f'  goto L_{arg};')
        elif typ=='ret':lines.append('  cpu->r[0]=acc; cpu->flags=f; return;')
        else:raise CFGError('bad source instruction')
    lines+=['}']
    return '\n'.join(lines)


def emit_private(out:Path,rows):
    if out.is_symlink() or not out.is_dir() or any(out.iterdir()):
        raise CFGError('private output must be a new empty directory')
    if not 1<=len(rows)<=MAX_FUNCTIONS:
        raise CFGError('invalid private source selection size')
    for row in rows:
        if parse_cfg(row['code'])!=row['ins']:
            raise CFGError('private game instruction identity drift')
    table=['/* GAME-DERIVED SOURCE: PRIVATE, NEVER PUBLISH */',
           '#include "recomp_abi.h"',
           *[f'extern void native_branch_{i}(BbCpu *cpu);' for i in range(len(rows))],
           *[f'static RcFn direct_{i}=native_branch_{i};' for i in range(len(rows))],
           'static const RcFunction table[]={',
           *[f'{{{r["start"]}ull,{r["size"]}ull,0,native_branch_{i},&direct_{i}}},' for i,r in enumerate(rows)],
           '};',
           '__attribute__((visibility("default"))) const RcFunction *bb_recomp_init(const RcApi *api,size_t *count) {',
           '  if(!api||!count||api->version!=BB_RECOMP_API_VERSION) return 0;',
           '  *count=sizeof(table)/sizeof(table[0]); return table;','}']
    logic=['/* GAME-DERIVED SOURCE: PRIVATE, NEVER PUBLISH */',
           '#include "recomp_abi.h"','#include <stdint.h>','#include <stddef.h>',
           'union V { unsigned char b[32]; float f[8]; };',
           'struct BbCpu { uint64_t r[16]; uint64_t rip; uint64_t flags; union V v[16]; };',
           '_Static_assert(offsetof(struct BbCpu,r)==0&&offsetof(struct BbCpu,rip)==128&&offsetof(struct BbCpu,flags)==136&&offsetof(struct BbCpu,v)==144, "pinned upstream prefix");',
           'static uint64_t bits_szp(uint32_t x){return (x==0?0x40ull:0ull)|(x&0x80000000u?0x80ull:0ull)|(__builtin_parity((unsigned)(x&255))==0?4ull:0ull);}',
           'static uint64_t flags_cmp32(uint32_t a,uint32_t b,uint64_t old){',
           '  uint32_t result=a-b;',
           '  uint64_t ov=(((a^b)&(a^result)&0x80000000u)!=0)?0x800ull:0ull;',
           '  return (old&~0x8c5ull)|bits_szp(result)|(a<b?1ull:0ull)|ov;',
           '}',
           'static uint64_t flags_test32(uint32_t a,uint64_t old){return (old&~0x8c5ull)|bits_szp(a);}',
           *[_function_c(i,r) for i,r in enumerate(rows)]]
    (out/'recomp.c').write_text('\n'.join(table)+'\n',encoding='utf-8')
    (out/'recomp_1.c').write_text('\n'.join(logic)+'\n',encoding='utf-8')


def probe_compiled(so:Path,rows):
    """Use upstream public RcApi v4 prefix, not whole production BbCpu ABI."""
    library=ctypes.CDLL(str(so))
    try:
        class V(ctypes.Union):_fields_=[('b',ctypes.c_ubyte*32),('f',ctypes.c_float*8)]
        class Cpu(ctypes.Structure):_fields_=[('r',ctypes.c_uint64*16),('rip',ctypes.c_uint64),('flags',ctypes.c_uint64),('v',V*16)]
        class Fn(ctypes.Structure):_fields_=[('offset',ctypes.c_uint64),('size',ctypes.c_uint64),('hash',ctypes.c_uint64),('fn',ctypes.c_void_p),('direct',ctypes.c_void_p)]
        class Api(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('image_base',ctypes.c_uint64),('step',ctypes.c_void_p),('call',ctypes.c_void_p),('tail',ctypes.c_void_p),('bail',ctypes.c_void_p),('trace',ctypes.c_void_p)]
        init=library.bb_recomp_init
        init.argtypes=[ctypes.POINTER(Api),ctypes.POINTER(ctypes.c_size_t)]
        init.restype=ctypes.POINTER(Fn)
        count=ctypes.c_size_t()
        table=init(ctypes.byref(Api(version=4)),ctypes.byref(count))
        if not table or count.value!=len(rows):
            raise CFGError('native library ABI table mismatch')
        verified=0
        for i,row in enumerate(rows):
            if table[i].offset!=row['start'] or table[i].size!=row['size'] or not table[i].fn:
                raise CFGError('native game source table lost descriptor')
            method=ctypes.CFUNCTYPE(None,ctypes.POINTER(Cpu))(table[i].fn)
            for val in test_values():
                cpu=Cpu();cpu.r[7]=val;cpu.r[0]=0xdeadbeef12345678;cpu.flags=0x123456789abcdef0
                expected,flags=simulate(row['ins'],val,initial_rax=cpu.r[0],initial_flags=cpu.flags)
                method(ctypes.byref(cpu))
                if cpu.r[0]!=expected or (cpu.flags&DEF_FLAGS)!=(flags&DEF_FLAGS):
                    raise CFGError('native compiled C branch/flags differs from original CPU model')
                verified+=1
        return verified
    finally:
        if sys.platform=='win32':
            import _ctypes
            _ctypes.FreeLibrary(library._handle)
            library._handle=0


def compile_linux(out:Path,rows):
    target=out.parent/'private_branch_test.so'
    cmd=['clang','-std=c11','-O2','-fPIC','-shared','-I',str(v189.abi_dir()),
         str(out/'recomp.c'),str(out/'recomp_1.c'),'-o',str(target)]
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    except (OSError,subprocess.TimeoutExpired) as e:
        raise CFGError('local native C compiler unavailable or timed out') from e
    if p.returncode:
        raise CFGError('private branch C could not compile on native host')
    return probe_compiled(target,rows)


def main():
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--eboot',type=Path,required=True)
    p.add_argument('--private-output-dir',type=Path,required=True)
    a=p.parse_args()
    image,starts=v189.load_original(a.eboot)
    rows=select(image,starts)
    cpu=original_cpu_oracle(rows)
    emit_private(a.private_output_dir,rows)
    compiled=compile_linux(a.private_output_dir,rows)
    print(json.dumps({'stage':'v191','verified_game_image':True,
                      'actual_private_game_branch_functions':len(rows),
                      'real_cpu_full_return_and_flags_compared':cpu,
                      'native_compiled_c_function_and_flags_compared':compiled,
                      'game_derived_windows_dll_executed':False,
                      'full_game_boot_or_online_verified':False},separators=(',',':')))

if __name__=='__main__':
    try:
        main()
    except (CFGError,v189.ProofError) as error:
        print('V191_SAFE_REJECTION',type(error).__name__,file=sys.stderr)
        raise SystemExit(2)
