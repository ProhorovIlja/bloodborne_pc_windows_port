# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline build of the unified register/load dispatch, including exact tail aliases."""
from alu_v488 import find as find_alu, emit as emit_alu, with_tail_aliases
from graph_v485 import graph, emit as emit_graph
from load_v486 import find, emit as emit_loads


def prepare(image, x, roots):
    roots=sorted(set(roots))
    regs,_=graph(image,x,roots)
    loads=list(find(image,x,roots))
    routes={a:a for a,*_ in loads}
    if not regs or not routes or regs.keys() & routes.keys():
        raise ValueError('empty or ambiguous generated families')
    _,_,off,base,_,size,_,_=x
    pending={}
    for a,b in zip(roots,roots[1:]+[base+size]):
        if a in routes or a in regs:
            continue
        p=off+a-base
        code=image[p:p+min(9,b-a)]
        skip=4 if code.startswith(b'\xf3\x0f\x1e\xfa') else 0
        code=code[skip:]
        if not code:
            continue
        n={0xe9:5,0xeb:2}.get(code[0],0)
        if n and len(code)>=n:
            pending[a]=a+skip+n+int.from_bytes(code[1:n],'little',signed=True)
    for _ in range(8):
        wave={a:routes[t] for a,t in pending.items() if t in routes}
        if not wave:
            break
        routes.update(wave)
        for a in wave:
            del pending[a]
    return regs,loads,dict(sorted(routes.items()))


def emit_routes(routes, out):
    print('static const struct {uint64_t id,target;} memory_routes[]={',file=out)
    for a,t in routes.items():
        print(f'{{UINT64_C({a}),UINT64_C({t})}},',file=out)
    print('};',file=out)


def main():
    import argparse
    import hashlib
    import mmap
    from pathlib import Path
    import struct
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
            roots=g['entry']|g['unwind']|g['constructors']
            regs,loads,routes=prepare(im,x,roots)
            excluded=regs.keys()|routes.keys()
            leaves=list(find_alu(im,x,roots,excluded))
            alu=with_tail_aliases(im,x,roots,leaves,excluded)
        if not alu:
            raise ValueError('no ALU functions')
        dst.mkdir(mode=0o700)
        for name,emit,rows in (('native.c',emit_graph,regs),('loads.c',emit_loads,loads),('routes_v487.inc',emit_routes,routes),('alu.c',emit_alu,alu)):
            with (dst/name).open('x',encoding='ascii') as f:
                emit(rows,f)
        print(f'alu_leaves={len(leaves)} alu_aliases={len(alu)-len(leaves)} register_ids={len(regs)} memory_ids={len(loads)} memory_aliases={len(routes)-len(loads)}')
    except (OSError,ValueError,struct.error,KeyError):
        print('V488 refused: input, output or provenance error',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
