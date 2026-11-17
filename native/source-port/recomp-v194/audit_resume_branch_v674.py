# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline leaf emitter for setjmp resumes beginning with TEST EAX,EAX; JZ/JNZ.

Emits a native next-PC decision only, not flags, state restoration or the target
block. Unrecognized sites are explicitly omitted and counted. Keep output local.
"""
import argparse
import json
from pathlib import Path

from audit_setjmp_v673 import audit


def decode(blob, offset, pc):
    code = blob[offset:offset+8]
    if len(code) != 8 or code[:2] != b'\x85\xc0':
        return None
    if code[2] in (0x74, 0x75):
        length, cond = 4, code[2]
    elif code[2] == 0x0f and code[3] in (0x84, 0x85):
        length, cond = 8, code[3]
    else:
        return None
    fallthrough = pc+length
    target = fallthrough+int.from_bytes(code[length-(1 if length==4 else 4):length],
                                        'little', signed=True)
    if cond & 1:
        return fallthrough, target
    return target, fallthrough


def emit(rows):
    lines = ['#include <stdint.h>',
             'int bb_resume_branch(uint64_t pc, uint32_t eax, uint64_t *next) {',
             '    switch (pc) {']
    for pc, zero, nonzero in sorted(rows):
        lines.append(f'    case 0x{pc:x}: *next = eax ? 0x{nonzero:x} : 0x{zero:x}; return 1;')
    return '\n'.join(lines+['    default: return 0;', '    }', '}', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot', type=Path)
    parser.add_argument('--emit-c', type=Path, help='new local C file; never committed')
    args = parser.parse_args()
    resumes = []
    audit(args.eboot, resumes=resumes)
    blob = args.eboot.read_bytes()
    rows = [(pc, *branch) for pc, offset in resumes
            if (branch := decode(blob, offset, pc)) is not None]
    if args.emit_c:
        with args.emit_c.open('x') as out:
            out.write(emit(rows))
    print(json.dumps(dict(resumes=len(resumes), emitted=len(rows),
                          unsupported=len(resumes)-len(rows))))


if __name__ == '__main__':
    main()
