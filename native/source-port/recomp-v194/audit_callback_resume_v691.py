# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline generation for nonzero callback continuations of the attested dump."""
import argparse
from pathlib import Path
from struct import unpack_from

from audit_setjmp_v673 import audit


def decode(code):
    if not code.startswith(bytes.fromhex('85c074')):
        return None
    end = 4+unpack_from('<b',code,3)[0]
    if end not in (24,35):
        return None
    wide = end == 35
    p = 4
    target = None
    for prefix, op in (('488b43304885c0','84'), ('8b7b3885ff','84'), ('ffd0','e9')):
        prefix = bytes.fromhex(prefix)
        if not code.startswith(prefix,p):
            return None
        p += len(prefix)
        if op == '84':
            jump = b'\x0f\x84' if wide else b'\x74'
        else:
            jump = b'\xe9' if wide else b'\xeb'
        if not code.startswith(jump,p):
            return None
        p += len(jump)
        n = 4 if wide else 1
        dst = p+n+int.from_bytes(code[p:p+n],'little',signed=True)
        p += n
        if dst < end or dst >= len(code):
            return None
        if target is None:
            target = dst
        if target != dst:
            return None
    tail = bytes.fromhex('488b034889df4c89f6ff50088b43384883c4085b')
    pops = bytes.fromhex(('415c415d' if wide else '')+'415e415f5dc3')
    if p != end or not code.startswith(tail+pops,target):
        return None
    return wide, code[4:end], target-4, code[target:target+15]


def scan(path):
    sites = []
    audit(path,resumes=sites)
    blob = path.read_bytes()
    return [(pc,*row) for pc,off in sites if (row := decode(blob[off:off+384]))]


def emit(rows):
    lines = ['#include "callback_resume_v691.h"',
             'const struct bb_callback_edge_v691 *bb_callback_lookup_v691(uint64_t pc) {',
             '    static const struct bb_callback_edge_v691 forms[] = {{0},{1}};',
             '    switch (pc) {']
    lines += [f'    case {pc:#x}: return &forms[{int(wide)}];' for pc,wide,*_ in sorted(rows)]
    return '\n'.join(lines+['    default: return NULL;', '    }', '}', ''])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot',type=Path)
    parser.add_argument('--emit-c',type=Path,help='new private C file')
    args = parser.parse_args()
    rows = scan(args.eboot)
    if args.emit_c:
        with args.emit_c.open('x') as out:
            out.write(emit(rows))
    print(f'{len(rows)} nonzero callback continuations')
