# SPDX-License-Identifier: GPL-2.0-or-later
"""Emit bounded native guarded continuations from a private 1.09 dump."""
import argparse
from pathlib import Path
from audit_guarded_resume_v683 import census


def emit(rows):
    lines = ['#include <stdint.h>', '#include <stddef.h>',
             '/* Return: 0 unsupported, 1 RET, 2 fatal stack-check edge. */',
             'int bb_guarded_resume(uint64_t pc, uint32_t *tls, uint64_t guard,',
             '    const uint64_t *frame, size_t words, size_t bp,',
             '    uint64_t nv[6], uint64_t *rax, uint64_t *next) {',
             '    if (!tls || !frame || !nv || !rax || !next || bp >= words) return 0;',
             '    switch (pc) {']
    for pc, _, zero, (clear, base, saved, src, skip, pops, fail) in sorted(rows):
        if saved >= 0 or saved % 8 or zero == {'rbx': 0, 'r12': 2, 'r13': 3}[base]:
            raise ValueError('unsupported canary frame or clobbered guard base')
        n = -saved//8
        end = skip+len(pops)
        lines += [f'    case 0x{pc:x}:',
                  f'        if (bp < {n} || words <= {end}) return 0;']
        if zero is not None:
            lines.append(f'        nv[{zero}]=0;')
        if clear:
            lines.append('        *tls=0;')
        lines += [f'        if (frame[bp-{n}] != guard) {{ *rax=guard; *next=0x{fail:x}; return 2; }}',
                  f'        *rax=(guard & ~UINT64_C(255)) | (uint8_t)nv[{src}];']
        lines += [f'        nv[{reg}]=frame[{i}];' for i, reg in enumerate(pops, skip)]
        lines += [f'        *next=frame[{end}]; return 1;']
    return '\n'.join(lines+['    default: return 0;', '    }', '}', ''])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('output', type=Path, help='new private C file, not for distribution')
    a = p.parse_args()
    rows = census(a.eboot)
    with a.output.open('x') as out:
        out.write(emit(rows))
    print(f'{len(rows)} guarded paths; missing/fatal edges are not guest fallbacks')
