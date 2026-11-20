# SPDX-License-Identifier: GPL-2.0-or-later
"""Lift attested V688 cleanup destinations; keep generated C private."""
import argparse
from pathlib import Path
from struct import unpack_from

from audit_cleanup_resume_v688 import scan


def decode(blob, pc, embedded, r14):
    p = pc + 0x4000
    code = blob[p:p+32]
    guard = code.startswith(b'\x49\x8b\x0e\x48\x3b\x4d\xe8\x75\x09')
    at = 9 if guard else 0
    if r14:
        if not code.startswith(b'\x44\x88\xf0', at):
            raise ValueError('missing AL result')
        at += 3
    skip = 0
    if code.startswith(b'\x48\x83\xc4', at):
        skip = code[at+3]//8
        if code[at+3] not in (8, 16):
            raise ValueError('unexpected stack adjustment')
        at += 4
    pops = (0, 4, 1) if code.startswith(b'\x5b\x41\x5e\x5d\xc3', at) else (0, 1)
    suffix = b'\x5b\x41\x5e\x5d\xc3' if len(pops)==3 else b'\x5b\x5d\xc3'
    if not code.startswith(suffix, at):
        raise ValueError('unexpected epilogue')
    end = at+len(suffix)
    fail = None
    if guard:
        if not embedded or r14 or end != 18 or code[end] != 0xe8:
            raise ValueError('unexpected stack-check edge')
        fail = pc+end+5+unpack_from('<i',code,end+1)[0]
    return skip, pops, fail, code[:end]


def emit(rows):
    lines = ['#include <stdint.h>', '#include <stddef.h>',
             '/* 0: unsupported; 1: RET; 2: fatal edge. AL, not full RAX, is exported. */',
             'int bb_cleanup_tail(uint64_t pc, uint64_t canary, const uint64_t *f,',
             '    size_t words, size_t bp, uint64_t nv[6], uint8_t *al,',
             '    uint64_t *next, size_t *consumed) {',
             '    if (!f || !nv || !al || !next || !consumed) return 0;',
             '    switch (pc) {']
    for pc, r14, (skip, pops, fail, _) in sorted(rows):
        n = skip+len(pops)+1
        lines += [f'    case {pc:#x}:', f'        if (words < {n}) return 0;']
        if fail is not None:
            lines += ['        if (bp < 3 || bp >= words) return 0;',
                      f'        if (f[bp-3] != canary) {{ *next={fail:#x}; *consumed=0; return 2; }}']
        if r14:
            lines.append('        *al=(uint8_t)nv[4];')
        lines += [f'        nv[{r}]=f[{i}];' for i,r in enumerate(pops,skip)]
        lines += [f'        *next=f[{n-1}]; *consumed={n}; return 1;']
    return '\n'.join(lines+['    default: return 0;', '    }', '}', ''])


def load(path):
    blob, prefixes = scan(path)
    return [(dst, r14, decode(blob,dst,embedded,r14))
            for _,dst,embedded,r14,*_ in prefixes]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot', type=Path)
    parser.add_argument('--emit-c', type=Path)
    args = parser.parse_args()
    rows = load(args.eboot)
    if args.emit_c:
        with args.emit_c.open('x') as out:
            out.write(emit(rows))
    print(f'{len(rows)} cleanup destinations, {sum(t[2] is not None for _,_,t in rows)} guarded')
