# SPDX-License-Identifier: GPL-2.0-or-later
"""Generate and compare two remaining guarded nonzero continuations offline."""
from hashlib import sha256
from struct import unpack_from

from audit_setjmp_v673 import audit

# Resume, branch prefix, target delta, success opcodes, frame and object layout.
FORMS = (
    (0x689ae, '89c131c085c90f85', 0x68af4,
     (24, 'f3d71c3c3b70454aea2c31a7256495c15f8ddc9717269e57c4b2b1be09b4c132'),
     12, 6, 7, (0,2,3,4,5,1), False),
    (0x210ae09, '85c07509', 0x210ae16,
     (43, '5c02801b3dbfb431ad62fca00e0bc1d40b65b660efe6c8fc57b72f7226bfdfa6'),
     20, 15, 16, (0,2,4,5,1), True),
)


def scan(path):
    sites = []
    audit(path, resumes=sites)
    blob = path.read_bytes()
    offsets = dict(sites)
    for pc, prefix, target, body, bp, guard, skip, pops, restore in FORMS:
        start = offsets[pc]
        lead = bytes.fromhex(prefix)
        if blob[start:start+len(lead)] != lead:
            raise ValueError('unexpected nonzero branch')
        rel = 4 if not restore else 0  # the short JNE displacement is in lead
        delta = unpack_from('<i', blob, start+len(lead))[0] if rel else lead[-1]
        if pc+len(lead)+rel+delta != target:
            raise ValueError('unexpected nonzero target')
        at = start+target-pc
        size, digest = body
        code = blob[at:at+size]
        if sha256(code).hexdigest() != digest or blob[at+size:at+size+1] != b'\xe8':
            raise ValueError('unexpected guarded epilogue')
        fatal = target+len(code)+5+unpack_from('<i', blob, at+len(code)+1)[0]
        if fatal != 0x2bbe4f8:
            raise ValueError('unexpected failure edge')
        yield pc, code, bp, guard, skip, pops, restore, fatal


def emit(rows):
    out = ['#include <stdint.h>', '#include <stddef.h>', '#include <string.h>',
           '/* 0 miss, 1 RET, 2 terminal guard edge. No guest dispatch. */',
           'int bb_guard_tail693(uint64_t pc, uint32_t v, unsigned char *obj, size_t len,',
           '  uint64_t guard, const uint64_t *f, size_t n, uint64_t regs[6],',
           '  uint64_t *rax, uint64_t *next, size_t *used) {',
           '    if (!v || !f || !regs || !rax || !next || !used) return 0;',
           '    (void)obj; (void)len;', '    switch (pc) {']
    for pc, _, _, slot, skip, pops, restore, fatal in rows:
        n = skip+len(pops)+1
        out += [f'    case {pc:#x}:', f'        if (n < {n}) return 0;']
        if restore:
            out += ['        if (!obj || len < 0x98) return 0;',
                    '        memcpy(obj+0x90, f+1, 8);', '        *rax = (uint32_t)f[14];']
        else:
            out += ['        *rax = 0;']
        out += [f'        if (f[{slot}] != guard) {{ *next={fatal:#x}; *used=0; return 2; }}']
        out += [f'        regs[{r}] = f[{i}];' for i,r in enumerate(pops,skip)]
        out += [f'        *next = f[{n-1}]; *used = {n}; return 1;']
    return '\n'.join(out+['    default: return 0;', '    }', '}', ''])
