# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline lowering of exact XOR-zero, MOV AL, and LEA RDI leaves."""
import struct


def decode(raw):
    if raw[:3] in (b'\x31\xc0\xc3',b'\x33\xc0\xc3'):
        return 3,'0','(flags & ~UINT64_C(0x8c5)) | 0x44',0x8c5
    if raw[:4] in (b'\x48\x31\xc0\xc3',b'\x48\x33\xc0\xc3'):
        return 4,'0','(flags & ~UINT64_C(0x8c5)) | 0x44',0x8c5
    if len(raw)>=3 and raw[0]==0xb0 and raw[2]==0xc3:
        return 3,f'(rax & ~UINT64_C(255)) | {raw[1]}','flags',0x8d5
    for mod,n in ((7,3),(0x47,4),(0x87,7)):
        if len(raw)>n and raw[:3]==bytes((0x48,0x8d,mod)) and raw[n]==0xc3:
            disp=int.from_bytes(raw[3:n],'little',signed=True)
            return n+1,f'rdi + UINT64_C({disp % 2**64})','flags',0x8d5
    return None


def find(image, x, seeds):
    _,_,off,base,_,size,_,_=x
    if not 0<size<=len(image) or not 0<=off<=len(image)-size:
        raise ValueError('invalid RX span')
    for a in sorted(set(seeds)):
        p=a-base
        if not 0<=p<size:
            raise ValueError('seed outside RX')
        raw=image[off+p:off+min(p+15,size)]
        skip=4 if raw.startswith(b'\xf3\x0f\x1e\xfa') else 0
        d=decode(raw[skip:])
        if d:
            n,v,f,m=d
            yield a,raw[:skip+n],v,f,m


def emit(rows,out):
    if not rows or any(a[0]>=b[0] for a,b in zip(rows,rows[1:])):
        raise ValueError('expected sorted nonempty leaves')
    p=lambda s:print(s,file=out)
    p('#include "leaf_v484.h"')
    for i,(_,_,v,f,m) in enumerate(rows):
        p(f'static struct bb_result_v484 f{i}(uint64_t rax,uint64_t rdi,uint64_t flags) {{')
        p(f' (void)rax; (void)rdi; return (struct bb_result_v484){{{v}, {f}, {m}}}; }}')
    p('static const struct { uint64_t id; struct bb_result_v484 (*fn)(uint64_t,uint64_t,uint64_t); } table[]={')
    for i,(a,*_) in enumerate(rows):
        p(f' {{UINT64_C({a}), f{i}}},')
    p('};')
    p('int bb_call_v484(uint64_t id,uint64_t a,uint64_t d,uint64_t f,struct bb_result_v484 *out) {')
    p(' size_t lo=0,hi=sizeof table/sizeof table[0];')
    p(' if(!out) return 0;')
    p(' while(lo<hi) {size_t m=lo+(hi-lo)/2; if(table[m].id<id) lo=m+1; else hi=m;}')
    p(' if(lo==sizeof table/sizeof table[0] || table[lo].id!=id) return 0;')
    p(' *out=table[lo].fn(a,d,f); return 1; }')


def main():
    import argparse
    import hashlib
    import mmap
    from pathlib import Path
    import sys
    from census_v480 import census
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--first-load-slot',type=lambda s:int(s,0),required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        dst=a.output.absolute()
        if dst.exists() or any(x.is_symlink() or (x/'.git').exists() for x in (dst,*dst.parents,*dst.resolve().parents)):
            raise ValueError
        if a.elf.is_symlink() or not a.elf.is_file() or not 64<=a.elf.stat().st_size<=512<<20:
            raise ValueError
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            if hashlib.sha256(im).hexdigest()!=a.sha256:
                raise ValueError
            e={}
            g,_=census(im,a.first_load_slot,evidence=e)
            x=e['rx']
            if any(x[3]-7<=s<x[3]+x[5] for s in e['relocs']):
                raise ValueError
            rows=list(find(im,x,g['entry']|g['unwind']|g['constructors']))
        if not rows:
            raise ValueError
        dst.mkdir(mode=0o700)
        with (dst/'leaves.c').open('x',encoding='ascii') as f:
            emit(rows,f)
        print('emitted_leaves='+str(len(rows)))
    except (OSError,ValueError,struct.error,KeyError):
        print('V484 refused: input, output or provenance error',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
