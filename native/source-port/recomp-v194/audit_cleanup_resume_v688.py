# SPDX-License-Identifier: GPL-2.0-or-later
"""Generate cleanup edges from attested direct setjmp continuations."""
import argparse
from pathlib import Path
from struct import unpack_from

from audit_setjmp_v673 import audit

THUNK = 0x3ada00
FLAG = bytes.fromhex('8a831004000024fc0c02888310040000')


def decode(blob, pc, off):
    code = blob[off:off+128]
    p = 0
    if code.startswith(bytes.fromhex('4c8d7308')):
        p, arg = 4, bytes.fromhex('4c89f7')
    elif code.startswith(bytes.fromhex('488d7b08')):
        p, arg = 4, b''
    else:
        arg = bytes.fromhex('4889df')
    embedded = bool(p)
    if code[p:p+3] != b'\x85\xc0\x74':
        return None
    zero = p+4+unpack_from('<b',code,p+3)[0]
    p += 4
    if not code.startswith(arg+b'\xe8', p):
        return None
    call = p+len(arg)
    p = call+5
    if pc+p+unpack_from('<i',code,call+1)[0] != THUNK:
        return None
    if embedded:
        if not code.startswith(FLAG,p):
            return None
        p += len(FLAG)
    r14 = embedded and code.startswith(b'\x45\x31\xf6',p)
    op = b'\x45\x31\xf6' if r14 else b'\x31\xc0'
    if not code.startswith(op+b'\xeb',p) or p+len(op)+2 != zero:
        return None
    target = zero+unpack_from('<b',code,zero-1)[0]
    if not zero <= target < len(code):
        return None
    return pc, pc+target, embedded, r14, call, code[:zero-2]


def scan(path):
    sites = []
    audit(path, resumes=sites)
    blob = path.read_bytes()
    return blob, [row for pc, off in sites if (row := decode(blob,pc,off)) is not None]


def emit(rows):
    lines = ['#include "cleanup_resume_v688.h"',
             'const struct bb_cleanup_edge_v688 *bb_cleanup_lookup_v688(uint64_t pc) {',
             '    switch (pc) {']
    for pc, target, embedded, r14, *_ in sorted(rows):
        lines += [f'    case {pc:#x}: {{',
                  f'        static const struct bb_cleanup_edge_v688 edge = '
                  f'{{{pc:#x}, {target:#x}, {int(embedded)}, {int(r14)}}};',
                  '        return &edge;', '    }']
    return '\n'.join(lines+['    default: return NULL;', '    }', '}', ''])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('--emit-c', type=Path, help='new private C file; do not distribute')
    a = p.parse_args()
    _, rows = scan(a.eboot)
    if a.emit_c:
        with a.emit_c.open('x') as f:
            f.write(emit(rows))
    print(f'{len(rows)} cleanup prefixes; destination blocks are not included')
