# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline TLS layout and local DTPMOD64 plan for a fixed module load order."""


def plan(images):
    offset = 0
    blocks, patches = [], {}
    for name, im in images.items():
        tls = [p for p in im['ph'] if p['type'] == 7]
        writable = [p for p in im['ph'] if p['type'] == 1 and p['flags'] == 6]
        rows = [(s,k,i,a) for s,k,i,a in im['relocs'] if k in (16,17,18)]
        if not tls and not rows:
            continue
        if len(tls) != 1 or len(writable) != 1:
            raise ValueError('unsupported TLS layout')
        t, w = tls[0], writable[0]
        v, f, n, a, o = (t[k] for k in ('vaddr','filesz','memsz','align','offset'))
        delta = v-w['vaddr']
        if not (0 <= f <= n <= 1 << 20 and n and 0 < a <= 65536 and not a & (a-1)
                and v % a == o % a and 0 <= delta <= w['memsz']-n
                and o == w['offset']+delta and 0 <= o <= len(im['elf'])-f
                and (not f or delta+f <= w['filesz'])):
            raise ValueError('invalid TLS template')
        # Match the PS4Recomp legacy variant-II layout, not modern FreeBSD.
        offset = (offset+n+a-1) & -a
        if offset > 16 << 20:
            raise ValueError('TLS area too large')
        idx = len(blocks)+1
        blocks.append((name, idx, offset, n, a, bytes(im['elf'][o:o+f])))
        end = w['vaddr']
        for slot, kind, sym, addend in sorted(rows):
            if (kind != 16 or addend or not end <= slot <= w['vaddr']+w['memsz']-8
                    or slot < v+n and v < slot+8 or not 0 <= sym < len(im['symbols'])):
                raise ValueError('unsupported TLS relocation')
            end = slot+8
            if sym:
                s = im['symbols'][sym]
                if (s['name'], s['type'], s['binding'], s['section'], s['value'], s['size']) != ('',3,0,0,0,0):
                    raise ValueError('TLS symbol is not the local section marker')
            patches[name, slot-w['vaddr']] = idx
    return blocks, patches


def initialize(blocks):
    """Return one fresh template buffer and the logical thread-pointer position.

    A native allocator must align the actual thread pointer; this is not a TCB.
    """
    align = max((b[4] for b in blocks), default=1)
    tp = (max((b[2] for b in blocks), default=0)+align-1) & -align
    area = bytearray(tp)
    for _, _, off, _, _, data in blocks:
        start = tp-off
        area[start:start+len(data)] = data
    return area, tp
