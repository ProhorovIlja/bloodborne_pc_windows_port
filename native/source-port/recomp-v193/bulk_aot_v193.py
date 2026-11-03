#!/usr/bin/env python3
"""V193: offline bulk AOT of ONLY exact, bounded Bloodborne 1.09 leaf grammars.

Game-derived C, function offsets, private binaries and code bytes MUST remain
private. Do not upload either generated files or private manifests to GitHub.
The compiler accepts only a complete clean original Bloodborne 1.09 image,
never trusts a raw partial function or a guessed CPU instruction.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import hashlib
import re
import sys

HERE=Path(__file__).resolve().parent

def _load(name: str, relative: str, fallback: str):
    choices=[HERE.parent/relative, HERE.parent/fallback]
    for p in choices:
        if p.is_file() and not p.is_symlink():
            spec=importlib.util.spec_from_file_location(name,p)
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise RuntimeError('source-locked predecessor verifier unavailable')

v189=_load('v189_bulk','recomp-v189/real_leaf_recomp_v189.py','native_real_leaf_v189/real_leaf_recomp_v189.py')
v190=_load('v190_bulk','recomp-v190/nontrivial_leaves_v190.py','native_real_leaf_v190/nontrivial_leaves_v190.py')

KINDS=('zero32','imm32','identity64','identity32',*v190.KINDS)
MAX_SHARD=512
MAX_ROWS=20000
CPU_FLAGS=0x8c5

class BulkError(ValueError): pass

def classify(frame: bytes):
    """Return (kind, immediate) ONLY for a fully checked 16-byte FDE body.

    All trailing bytes must be recognized canonical NOP padding. No calls,
    arbitrary branches, unsafe offsets, partial decode or unknown instructions.
    """
    if len(frame)!=16: return None
    legacy=v189.identify(frame)
    if legacy and legacy[0] in KINDS[:4] and v190.valid_nops(frame[legacy[1]:]):
        return legacy[0],legacy[2]
    recent=v190.decode(frame)
    if recent and recent[0] in v190.KINDS:
        return recent[0],recent[2]
    return None


def strict_leaf_hash(frame:bytes)->int:
    """Source-locked FNV-1a candidate for an exact, fully decoded V193 FDE.

    Upstream src/cpu/recomp.c::bbcpu_recomp_hash mixes every decoded instruction
    byte, except a special TCB/FS/GS load. None of the ten accepted grammars
    permits that exception; the complete recognized 16-byte body and its NOP
    tail contain only valid instructions. This is NOT a substitute for an
    independent live upstream-Zydis comparison or full-game hash coverage.
    """
    if classify(frame) is None:
        raise BulkError('hash requires a strictly recognized 16-byte FDE')
    h=0xcbf29ce484222325
    for byte in frame:
        h=((h ^ byte)*0x100000001b3)&0xffffffffffffffff
    return h


def census(image:bytes,starts:list[int]):
    """Classify every complete, properly sorted original FDE interval.

    This is a grammar census, NOT a correctness assertion or function coverage
    ratio. FDE padding and uncovered functions are explicitly omitted.
    """
    if len(starts)<2 or len(starts)>v189.MAX_FDE:
        raise BulkError('invalid original FDE count')
    if any(a>=b or a<0 or b>len(image) for a,b in zip(starts,starts[1:])):
        raise BulkError('FDE order or bounds invalid')
    rows=[]
    counts={k:0 for k in KINDS}
    for a,b in zip(starts,starts[1:]):
        if b-a!=16: continue
        frame=bytes(image[a:b]); hit=classify(frame)
        if hit is None: continue
        kind,value=hit
        if len(rows)>=MAX_ROWS:raise BulkError('bulk candidate budget exceeded')
        counts[kind]+=1
        # The row contains no game bytes after classification, only private
        # per-function metadata. It MUST NOT be published in GitHub or CI.
        rows.append((a,kind,value))
    return rows,counts


def split_chunks(rows, chunk_size:int):
    if not 1<=chunk_size<=MAX_SHARD or not 1<=len(rows)<=MAX_ROWS:
        raise BulkError('invalid private bulk shard size')
    if any(rows[i][0]>=rows[i+1][0] for i in range(len(rows)-1)):
        raise BulkError('function entries not strictly ordered')
    return [rows[i:i+chunk_size] for i in range(0,len(rows),chunk_size)]


def func_source(index:int, kind:str, imm:int, *, guest_return:bool=False)->str:
    if kind not in KINDS:raise BulkError('unexpected generated code grammar')
    prefix=f'void bb_native_{index}(BbCpu *cpu) {{ '
    if kind=='zero32':
        body='cpu->r[0]=0; cpu->flags=(cpu->flags&~0x8c5ull)|0x44ull;'
    elif kind=='imm32': body=f'cpu->r[0]={imm}ull;'
    elif kind=='identity64':body='cpu->r[0]=cpu->r[7];'
    elif kind=='identity32':body='cpu->r[0]=(uint32_t)cpu->r[7];'
    elif kind=='mem64':body=f'uint64_t v; __builtin_memcpy(&v,(const void*)(uintptr_t)(cpu->r[7]+{imm}),8); cpu->r[0]=v;'
    elif kind=='mem32':body=f'uint32_t v; __builtin_memcpy(&v,(const void*)(uintptr_t)(cpu->r[7]+{imm}),4); cpu->r[0]=v;'
    elif kind=='store64':body=f'__builtin_memcpy((void*)(uintptr_t)(cpu->r[7]+{imm}),&cpu->r[6],8);'
    elif kind=='lea64':body=f'cpu->r[0]=cpu->r[7]+{imm}ull;'
    elif kind=='sse32':body=f'__builtin_memset(cpu->v[0].b,0,32); __builtin_memcpy(cpu->v[0].b,(const void*)(uintptr_t)(cpu->r[7]+{imm}),4);'
    elif kind=='flags_eq32':
        body=('uint32_t x=(uint32_t)cpu->r[7]; '
              'unsigned pf=__builtin_parity((unsigned)(x&255))==0; '
              'cpu->flags=(cpu->flags&~0x8c5ull)|(x==0?0x40ull:0ull)|(x&0x80000000u?0x80ull:0ull)|(pf?0x4ull:0ull); '
              'cpu->r[0]=(cpu->r[0]&~255ull)|(x==0);')
    else:raise BulkError('unsupported')
    if guest_return:
        # Real guest RET semantics: pop the original x86-64 return address.
        # This is ONLY a prototype until the upstream original-code hash and
        # full runtime / guest stack boundary checks have been integrated.
        body += ('uint64_t guest_return_address; '
                 '__builtin_memcpy(&guest_return_address,(const void*)(uintptr_t)cpu->r[4],8); '
                 'cpu->r[4]+=8; cpu->rip=guest_return_address;')
    return prefix+body+' }'


def emit_private(out:Path, image:bytes, starts:list[int], rows:list[tuple], shard_size:int=256, *, guest_return:bool=False, upstream_hash_prototype:bool=False):
    """Validate EVERY row against real image/FDE before writing any source.

    Output folder must be empty, non-symlinked. Never uses game image as input
    to the compiler, only C emitted from fully recognized 16-byte functions.
    """
    if out.is_symlink() or not out.is_dir() or any(out.iterdir()):
        raise BulkError('private output directory must be new, empty and regular')
    # Avoid accidentally emitting game-derived source into a git checkout,
    # including worktrees where .git is a regular file. Refuse before writes.
    output_root=out.resolve(strict=True)
    if any((parent/'.git').exists() for parent in (output_root,*output_root.parents)):
        raise BulkError('private source output must be outside all git worktrees')
    if upstream_hash_prototype and not guest_return:
        raise BulkError('upstream hash prototype requires guest RET prototype')
    if not rows or len(rows)>MAX_ROWS:raise BulkError('bulk source row budget exceeded')
    fde={a:b for a,b in zip(starts,starts[1:])}
    for i,(addr,kind,imm) in enumerate(rows):
        if not isinstance(addr,int) or fde.get(addr)!=addr+16:
            raise BulkError('function is not an exact 16-byte original FDE')
        if classify(image[addr:addr+16])!=(kind,imm):
            raise BulkError('generated metadata fails source-exact grammar revalidation')
        if i and addr<=rows[i-1][0]:raise BulkError('not sorted or duplicate')
    shards=split_chunks(rows,shard_size)
    # Computed only after validating the exact source frame and FDE bounds.
    # Hashes are game-derived and are written only into the PRIVATE output.
    hashes=[strict_leaf_hash(image[addr:addr+16]) if upstream_hash_prototype else 0
            for addr,_,_ in rows]
    table=['/* USER PRIVATE derived from original game. DO NOT PUBLISH. */',
           '#include "recomp_abi.h"',
           *[f'extern void bb_native_{i}(BbCpu*);' for i in range(len(rows))],
           *[f'static RcFn native_direct_{i}=bb_native_{i};' for i in range(len(rows))],
           'static const RcFunction table[]={',
           *[f'{{{addr}ull,16ull,{hashes[i]}ull,bb_native_{i},&native_direct_{i}}},'
             for i,(addr,_,_) in enumerate(rows)],
           '};',
           '__attribute__((visibility("default"))) const RcFunction *bb_recomp_init(const RcApi *api,size_t *count){',
           'if(!api||!count||api->version!=BB_RECOMP_API_VERSION)return 0;',
           '*count=sizeof(table)/sizeof(table[0]);return table;',
           '}']
    begin=['/* USER PRIVATE derived from original game. DO NOT PUBLISH. */',
           '#include "recomp_abi.h"','#include <stdint.h>','#include <stddef.h>',
           'union V { unsigned char b[32]; float f[8]; };',
           'struct BbCpu { uint64_t r[16];uint64_t rip;uint64_t flags;union V v[16]; };',
           '_Static_assert(offsetof(struct BbCpu,r)==0 && offsetof(struct BbCpu,rip)==128 && offsetof(struct BbCpu,flags)==136 && offsetof(struct BbCpu,v)==144,"pinned upstream CPU prefix");']
    files={'recomp.c':'\n'.join(table)+'\n'}
    for i,chunk in enumerate(shards):
        offset=i*shard_size
        body=begin+[func_source(offset+j,k,imm,guest_return=guest_return) for j,(_,k,imm) in enumerate(chunk)]
        files[f'recomp_{i+1}.c']='\n'.join(body)+'\n'
    # All paths checked and content built before the first source write.
    for path,content in files.items():
        if len(content.encode('utf8')) > (64<<20):raise BulkError('source unit exceeded budget')
    for path,content in files.items():
        (out/path).write_text(content,encoding='utf8')
    # private manifest may contain game-code-derived function addresses; not public
    private={'image_sha256':v189.IMAGE_SHA,
             'count':len(rows),'shards':len(shards),'shard_size':shard_size,
             'guest_return_prototype':guest_return,
             'upstream_hash_prototype':upstream_hash_prototype,
             'functions':[[addr,kind,imm] for addr,kind,imm in rows],
             'sources_sha256':{name:hashlib.sha256(c.encode()).hexdigest() for name,c in files.items()}}
    (out/'PRIVATE_DO_NOT_UPLOAD_manifest.json').write_text(json.dumps(private,separators=(',',':'))+'\n',encoding='utf8')
    return {'status':'generated-private','recognized_functions':len(rows),
            'source_units':len(files),'kinds':len({kind for _,kind,_ in rows}),
            'guest_return_prototype':guest_return,
            'upstream_hash_prototype':upstream_hash_prototype,
            'upstream_code_hashes_ready':False,
            'complete_engine_proven':False,'whole_game_windows_boot_proven':False}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('--eboot',required=True,type=Path)
    ap.add_argument('--private-output-dir',required=True,type=Path)
    ap.add_argument('--shard-size',type=int,default=256)
    ap.add_argument('--guest-return-prototype',action='store_true',
                    help='Emit x86-64 guest RET stack/rip semantics (not ready for upstream runtime; hashes absent)')
    ap.add_argument('--upstream-hash-prototype',action='store_true',
                    help='Private strict-leaf FNV hashes; requires guest RET (not validated in live upstream runtime)')
    a=ap.parse_args(argv)
    try:
        image,starts=v189.load_original(a.eboot)
        rows,counts=census(image,starts)
        report=emit_private(a.private_output_dir,image,starts,rows,a.shard_size,
                            guest_return=a.guest_return_prototype,
                            upstream_hash_prototype=a.upstream_hash_prototype)
        report['by_grammar']=counts
        print(json.dumps(report,separators=(',',':')))
        return 0
    except (ValueError,RuntimeError,OSError,v189.ProofError) as exc:
        print(json.dumps({'status':'failure','reason':'unsupported original image, function source, output or budget'}))
        return 2

if __name__=='__main__':raise SystemExit(main())
