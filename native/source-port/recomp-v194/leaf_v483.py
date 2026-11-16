# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact register-only x86-64 leaves. No memory, flags, or fallback calls."""
import struct


def decode(raw):
    if raw[:4]==b'\xf3\x0f\x1e\xfa':
        raw=raw[4:]
    if raw[:1]==b'\xc3':
        return (1,'rax')
    if len(raw)>=6 and raw[0]==0xb8 and raw[5]==0xc3:
        return (6,str(struct.unpack_from('<I',raw,1)[0])+'ull')
    if len(raw)>=8 and raw[:3]==b'\x48\xc7\xc0' and raw[7]==0xc3:
        return (8,str(struct.unpack_from('<i',raw,3)[0]%2**64)+'ull')
    if len(raw)>=11 and raw[:2]==b'\x48\xb8' and raw[10]==0xc3:
        return (11,str(struct.unpack_from('<Q',raw,2)[0])+'ull')
    for prefix,mask in ((b'','(uint32_t)'),(b'\x48','')):
        for op in (0x89,0x8b):
            for reg,name in ((0,'rax'),(1,'rcx'),(2,'rdx'),(6,'rsi'),(7,'rdi')):
                modrm=0xc0+(reg*8 if op==0x89 else reg)
                seq=prefix+bytes((op,modrm,0xc3))
                if raw.startswith(seq):
                    return len(seq),mask+name
    return None


def find(image,offset,base,size,seeds):
    if not 0<size<=len(image) or not 0<=offset<=len(image)-size:
        raise ValueError('invalid RX span')
    for a in sorted(set(seeds)):
        p=a-base
        if not 0<=p<size:
            raise ValueError('seed outside RX')
        raw=image[offset+p:offset+min(p+15,size)]
        d=decode(raw)
        if d:
            n,expr=d
            yield a,raw[:n+4*raw.startswith(b'\xf3\x0f\x1e\xfa')],expr


def emit(rows,out):
    if not rows:
        raise ValueError('no matched leaves')
    print('#include <stdint.h>',file=out)
    print('typedef uint64_t (*leaf)(uint64_t,uint64_t,uint64_t,uint64_t,uint64_t);',file=out)
    for i,(_,_,expr) in enumerate(rows):
        print(f'static uint64_t f{i}(uint64_t rax,uint64_t rcx,uint64_t rdx,uint64_t rsi,uint64_t rdi) {{',file=out)
        print(f' (void)rax; (void)rcx; (void)rdx; (void)rsi; (void)rdi; return {expr}; }}',file=out)
    print('const leaf leaves[]={',file=out)
    for i in range(len(rows)):
        print(f' f{i},',file=out)
    print('};',file=out)
    print(f'const unsigned leaf_count={len(rows)}u;',file=out)


def main():
    import argparse
    import hashlib
    import mmap
    from pathlib import Path
    import sys
    from census_v480 import census, EH, PH
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--first-load-slot',type=lambda s:int(s,0),required=True)
    p.add_argument('--output',type=Path,required=True,help='new owner-local directory outside Git')
    a=p.parse_args()
    try:
        out=a.output.absolute()
        if out.exists() or any(x.is_symlink() or (x/'.git').exists() for x in (out,*out.parents,*out.resolve().parents)):
            raise ValueError('unsafe output')
        if a.elf.is_symlink() or not a.elf.is_file() or not EH.size<=a.elf.stat().st_size<=512<<20:
            raise ValueError('unsafe ELF')
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            if hashlib.sha256(im).hexdigest()!=a.sha256:
                raise ValueError('ELF identity mismatch')
            evidence={}
            groups,_=census(im,a.first_load_slot,evidence=evidence)
            x=evidence['rx']
            if any(x[3]-7<=a<x[3]+x[5] for a in evidence['relocs']):
                raise ValueError('relocated RX not supported')
            seeds=groups['entry']|groups['constructors']|groups['unwind']
            rows=list(find(im,x[2],x[3],x[5],seeds))
        if not rows:
            raise ValueError('no leaves')
        out.mkdir(mode=0o700)
        with (out/'leaves.c').open('x',encoding='ascii') as c:
            emit(rows,c)
        with (out/'ids.tsv').open('x',encoding='ascii') as t:
            print('guest_id\tlocal_index',file=t)
            for i,(a,_,_) in enumerate(rows):
                print(f'{a:#x}\t{i}',file=t)
        print(f'seeds={len(seeds)} emitted_leaves={len(rows)}')
    except (ValueError,OSError,struct.error,KeyError):
        print('V483 refused: input, output or provenance error',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
