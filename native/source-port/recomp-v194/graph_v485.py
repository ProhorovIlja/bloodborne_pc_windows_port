# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline AOT composition of exact register leaves and bounded direct wrappers."""
import leaf_v483
import leaf_v484


def graph(image,x,roots):
    _,_,off,base,_,size,_,_=x
    roots=sorted(set(roots))
    if not roots or not 0<size<=len(image) or not 0<=off<=len(image)-size or not base<=roots[0]<=roots[-1]<base+size:
        raise ValueError('invalid RX/roots')
    rows, pending={},{}
    for pc,end in zip(roots,roots[1:]+[base+size]):
        p=off+pc-base
        raw=image[p:p+min(end-pc,15)]
        old=leaf_v483.decode(raw)
        skip=4 if raw.startswith(b'\xf3\x0f\x1e\xfa') else 0
        if old:
            n,v=old
            rows[pc]=(raw[:skip+n],v,'flags',0x8d5,None)
            continue
        c=raw[skip:]
        new=leaf_v484.decode(c)
        if new:
            n,v,f,m=new
            rows[pc]=(raw[:skip+n],v,f,m,None)
            continue
        op=c[0] if c else 0
        n={0xe8:5,0xe9:5,0xeb:2}.get(op,0)
        if not n or len(c)<n+(op==0xe8) or op==0xe8 and c[n]!=0xc3:
            continue
        target=pc+skip+n+int.from_bytes(c[1:n],'little',signed=True)
        pending[pc]=(raw[:skip+n+(op==0xe8)],None,None,None,target)
    # Snapshot each wave: cycles, unknown destinations and depth >8 never emit.
    for _ in range(8):
        wave={pc:r for pc,r in pending.items() if r[-1] in rows}
        if not wave:
            break
        rows.update(wave)
        for pc in wave:
            del pending[pc]
    return dict(sorted(rows.items())),len(pending)


def emit(rows,out):
    if not rows:
        raise ValueError('empty graph')
    p=lambda s:print(s,file=out)
    p('#include "graph_v485.h"')
    ids={pc:i for i,pc in enumerate(sorted(rows))}
    sig='uint64_t rax,uint64_t rcx,uint64_t rdx,uint64_t rsi,uint64_t rdi,uint64_t flags'
    for i in ids.values():
        p(f'static struct bb_result_v484 f{i}({sig});')
    for pc,i in ids.items():
        _,v,f,m,t=rows[pc]
        if t is None:
            body=f'(void)rax;(void)rcx;(void)rdx;(void)rsi;(void)rdi;return (struct bb_result_v484){{{v},{f},{m}}};'
        else:
            body=f'return f{ids[t]}(rax,rcx,rdx,rsi,rdi,flags);'
        p(f'static struct bb_result_v484 f{i}({sig}){{{body}}}')
    p('static const struct { uint64_t id; struct bb_result_v484 (*fn)('+sig+'); } table[]={')
    for pc,i in ids.items():
        p(f'{{UINT64_C({pc}),f{i}}},')
    p('};')
    p('int bb_call_v485(uint64_t id,'+sig+',struct bb_result_v484 *out) {')
    p('size_t lo=0,hi=sizeof table/sizeof table[0]; if(!out) return 0;')
    p('while(lo<hi){size_t m=lo+(hi-lo)/2;if(table[m].id<id)lo=m+1;else hi=m;}')
    p('if(lo==sizeof table/sizeof table[0]||table[lo].id!=id)return 0;')
    p('*out=table[lo].fn(rax,rcx,rdx,rsi,rdi,flags);return 1;}')


def main():
    import argparse
    import hashlib
    import mmap
    from pathlib import Path
    import struct
    import sys
    from census_v480 import census
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',required=True,type=Path)
    p.add_argument('--sha256',required=True)
    p.add_argument('--first-load-slot',required=True,type=lambda s:int(s,0))
    p.add_argument('--output',required=True,type=Path)
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
            rows,missing=graph(im,x,g['entry']|g['unwind']|g['constructors'])
        if not rows:
            raise ValueError
        dst.mkdir(mode=0o700)
        with (dst/'native.c').open('x',encoding='ascii') as f:
            emit(rows,f)
        print(f'emitted_ids={len(rows)} direct_wrappers={sum(r[-1] is not None for r in rows.values())} declined_wrappers={missing}')
    except (OSError,ValueError,struct.error,KeyError):
        print('V485 refused: input, output or provenance error',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
