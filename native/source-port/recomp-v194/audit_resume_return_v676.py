# SPDX-License-Identifier: GPL-2.0-or-later
"""Emit simple returns-twice cleanup epilogues from the attested local dump."""
import argparse
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from audit_resume_block_v675 import blocks

GOT = 0x53e4318
HEAD = bytes.fromhex('64488b042500000000480305')
STORE = bytes.fromhex('c70000000000')
# Array indexes are RBX, RBP, R12, R13, R14, R15.
MOV = [(b'\x88\xd8', 0), (b'\x44\x88\xf0', 4), (b'\x44\x88\xf8', 5)]
POP = [(bytes.fromhex(x), i) for i, x in enumerate(('5b', '5d', '415c', '415d', '415e', '415f'))]


def decode(code, pc):
    if len(code) < 22 or not code.startswith(HEAD) or code[16:22] != STORE:
        return None
    if pc + 16 + unpack_from('<i', code, 12)[0] != GOT:
        return None
    pos = 22
    for op, src in MOV:
        if code.startswith(op, pos):
            pos += len(op)
            break
    else:
        return None  # e.g. stack canary path; never skip that check
    skip = int(code.startswith(b'\x48\x83\xc4\x08', pos))
    pos += skip * 4
    pops = []
    while len(pops) <= 6:
        if code[pos:pos+1] == b'\xc3' and pops and pops[-1] == 1:
            return src, skip, pops, code[:pos+1]
        for op, dst in POP:
            if code.startswith(op, pos) and dst not in pops:
                pops.append(dst)
                pos += len(op)
                break
        else:
            break
    return None


def scan(path):
    _, previous = blocks(path)
    blob = path.read_bytes()
    off, = unpack_from('<Q', blob, 32)
    num, = unpack_from('<H', blob, 56)
    ph = list(iter_unpack('<II6Q', blob[off:off+num*56]))
    rx, = [p for p in ph if p[0] == 1 and p[1] & 1]
    data, = [p for p in ph if p[0] == 1 and p[1] & 2 and p[3] <= GOT <= p[3]+p[5]-8]
    delta, = unpack_from('<q', blob, data[2]+GOT-data[3])
    targets = {t for _, t, _ in previous.values()}
    rows = {}
    for pc in sorted(targets):
        if rx[3] <= pc <= rx[3]+rx[5]-40:
            i = pc + rx[2] - rx[3]
            row = decode(blob[i:i+40], pc)
            if row:
                rows[pc] = row
    return previous, targets, rows, delta


def emit(rows):
    # TLS is already resolved by the caller. Stack words are read from a
    # bounded guest-frame representation, never popped from the host stack.
    lines = ['#include <stddef.h>', '#include <stdint.h>',
             'int bb_resume_return(uint64_t pc, uint32_t *tls, uint64_t tls_addr,',
             '    const uint64_t *stack, size_t words, uint64_t regs[6],',
             '    uint64_t *rax, uint64_t *next, size_t *consumed) {',
             '    if (!tls || !stack || !regs || !rax || !next || !consumed) return 0;',
             '    switch (pc) {']
    for pc, (src, skip, pops, _) in rows.items():
        count = skip+len(pops)+1
        lines += [f'    case 0x{pc:x}:', f'        if (words < {count}) return 0;',
                  f'        *tls = 0; *rax = (tls_addr & ~UINT64_C(255)) | (uint8_t)regs[{src}];']
        lines += [f'        regs[{r}] = stack[{i}];' for i, r in enumerate(pops, skip)]
        lines += [f'        *next = stack[{count-1}]; *consumed = {count}; return 1;']
    return '\n'.join(lines+['    default: return 0;', '    }', '}', ''])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('--emit-c', type=Path, help='new local C file; never commit output')
    a = p.parse_args()
    previous, targets, rows, delta = scan(a.eboot)
    if a.emit_c:
        with a.emit_c.open('x') as out:
            out.write(emit(rows))
    print(json.dumps(dict(unique_targets=len(targets), emitted=len(rows),
                          covered_paths=sum(t in rows for _, t, _ in previous.values()),
                          tls_delta=delta)))


if __name__ == '__main__':
    main()
