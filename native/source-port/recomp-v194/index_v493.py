# SPDX-License-Identifier: GPL-2.0-or-later
"""Build an exact ID index over a single set of generated AOT units."""
import re


def numeric_ids(text):
    # Emitters' row syntax, not an ELF input. Reject unexpected table shape.
    ids=[int(s) for s in re.findall(r'(?m)^ *\{UINT64_C\(([0-9]+)\),',text)]
    if not ids or any(a>=b for a,b in zip(ids,ids[1:])) or ids[-1]>=2**64:
        raise ValueError('invalid generated table')
    return ids


def emit_index(regs, loads, memory, alu, stores, out, *, rip=None):
    families=(regs,loads,alu,stores) if rip is None else (regs,loads,alu,stores,rip)
    route_bits=2 if rip is None else 3
    for ids in families:
        if not ids or any(not 0<=a<2**64 for a in ids) or any(a>=b for a,b in zip(ids,ids[1:])):
            raise ValueError('expected nonempty sorted unique family')
    maps={a:i for i,a in enumerate(loads)}
    if not set(memory.values())<=maps.keys() or any(memory.get(a)!=a for a in loads):
        raise ValueError('invalid memory routes')
    rows={}
    tables=[enumerate(regs),((maps[t],a) for a,t in memory.items()),enumerate(alu),enumerate(stores)]
    if rip is not None:
        tables.append(enumerate(rip))
    for tag, pairs in enumerate(tables):
        for n,a in pairs:
            if a in rows or not 0<=a<2**64 or not 0<=n<2**(32-route_bits):
                raise ValueError('ambiguous or out-of-range route')
            rows[a]=(n<<route_bits)|tag
    if not rows:
        raise ValueError('empty route index')
    p=lambda s:print(s,file=out)
    bits=32 if max(rows)<2**32 else 64
    p(f'static const uint{bits}_t bb_ids_v493[]={{')
    for a in sorted(rows):
        p(f'UINT{bits}_C({a}),')
    p('};')
    p('static const uint32_t bb_routes_v493[]={')
    for a in sorted(rows):
        p(f'UINT32_C({rows[a]}),')
    p('};')
    p(f'enum {{ BB_ROUTE_BITS_V493 = {route_bits} }};')
    return len(rows)


def write_index(directory, *, with_rip=False):
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
                          numeric_ids(read('stores.c')),out,
                          rip=numeric_ids(read('rip.c')) if with_rip else None)
