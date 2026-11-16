# SPDX-License-Identifier: GPL-2.0-or-later
"""Build an exact ID index over a single set of generated AOT units."""
import re


def numeric_ids(text):
    # Emitters' row syntax, not an ELF input. Reject unexpected table shape.
    ids=[int(s) for s in re.findall(r'(?m)^ *\{UINT64_C\(([0-9]+)\),',text)]
    if not ids or any(a>=b for a,b in zip(ids,ids[1:])) or ids[-1]>=2**64:
        raise ValueError('invalid generated table')
    return ids


def emit_index(regs, loads, memory, alu, stores, out):
    maps={a:i for i,a in enumerate(loads)}
    rows={}
    for tag, pairs in enumerate((enumerate(regs),((maps[t],a) for a,t in memory.items()),
                                enumerate(alu),enumerate(stores))):
        for n,a in pairs:
            if a in rows or not 0<=a<2**64 or not 0<=n<2**30:
                raise ValueError('ambiguous or out-of-range route')
            rows[a]=4*n+tag
    if not rows:
        raise ValueError('empty route index')
    p=lambda s:print(s,file=out)
    p('static const uint64_t bb_ids_v493[]={')
    for a in sorted(rows):
        p(f'UINT64_C({a}),')
    p('};')
    p('static const uint32_t bb_routes_v493[]={')
    for a in sorted(rows):
        p(f'UINT32_C({rows[a]}),')
    p('};')
    return len(rows)


def write_index(directory):
    def read(n):
        return (directory/n).read_text(encoding='ascii')
    route=read('routes_v487.inc')
    keys=numeric_ids(route)
    pairs=re.findall(r'(?m)^ *\{UINT64_C\(([0-9]+)\),UINT64_C\(([0-9]+)\)\},$',route)
    if [int(a) for a,_ in pairs]!=keys:
        raise ValueError('invalid memory routes')
    with (directory/'index_v493.inc').open('x',encoding='ascii') as out:
        return emit_index(numeric_ids(read('native.c')),numeric_ids(read('loads.c')),
                          {int(a):int(t) for a,t in pairs},numeric_ids(read('alu.c')),
                          numeric_ids(read('stores.c')),out)
