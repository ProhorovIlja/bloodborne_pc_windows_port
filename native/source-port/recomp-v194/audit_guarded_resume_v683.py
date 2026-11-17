# SPDX-License-Identifier: GPL-2.0-or-later
"""Classify guarded continuations in a private, attested Bloodborne dump."""
import argparse
from collections import Counter
import json
from pathlib import Path
from struct import unpack_from

from audit_resume_branch_v674 import decode
from audit_resume_return_v676 import GOT, HEAD, STORE, MOV, POP, scan
from audit_setjmp_v673 import audit

GUARD = {b'\x49\x8b\x04\x24': 'r12', b'\x49\x8b\x45\x00': 'r13',
         b'\x48\x8b\x03': 'rbx'}
XOR = {b'\x45\x31\xf6': 4}


def guarded(code, pc):
    clear = code.startswith(HEAD)
    i = 0
    if clear:
        if code[16:22] != STORE or pc+16+unpack_from('<i', code, 12)[0] != GOT:
            return None
        i = 22
    for op, base in GUARD.items():
        if code.startswith(op, i):
            i += len(op)
            break
    else:
        return None
    if code[i:i+3] != b'\x48\x3b\x45' or code[i+4:i+5] != b'\x75':
        return None
    saved = unpack_from('<b', code, i+3)[0]
    fail = i+6+unpack_from('<b', code, i+5)[0]
    i += 6
    src = None
    for op, candidate in MOV:
        if code.startswith(op, i):
            src = candidate
            i += len(op)
            break
    if code.startswith(b'\x48\x83\xc4', i):
        skip = unpack_from('<b', code, i+3)[0]
        i += 4
    elif code.startswith(b'\x48\x81\xc4', i):
        skip = unpack_from('<i', code, i+3)[0]
        i += 7
    else:
        return None
    pops = []
    while i < fail:
        if code[i:i+1] == b'\xc3':
            if (i+1 != fail or not pops or pops[-1] != 1 or skip < 0 or skip % 8
                    or code[fail:fail+1] != b'\xe8' or len(code) < fail+5):
                return None
            return (clear, base, saved, src, skip//8, tuple(pops),
                    pc+fail+5+unpack_from('<i', code, fail+1)[0])
        for op, dst in POP:
            if code.startswith(op, i) and dst not in pops:
                i += len(op)
                pops.append(dst)
                break
        else:
            return None
    return None


def census(path):
    blob = path.read_bytes()
    sites = []
    audit(path, resumes=sites)
    blocks, _, returns, _ = scan(path, resumes=sites)
    hits = []
    for pc, off in sites:
        branch = decode(blob, off, pc)
        if not branch:
            continue
        dest = branch[1]
        prior = blocks.get(dest)
        if prior:
            zeroed, dest, _ = prior
            if dest in returns:
                continue
            prefix = (0, 4, 5)[zeroed]
        else:
            prefix = None
            at = dest+0x4000
            for op, reg in XOR.items():
                if blob.startswith(op, at):
                    dest += len(op)
                    prefix = reg
                    break
        code = blob[dest+0x4000:dest+0x4050]
        shape = guarded(code, dest)
        if shape:
            hits.append((pc, dest, prefix, shape))
    return hits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    a = p.parse_args()
    hits = census(a.eboot)
    print(json.dumps(dict(paths=len(hits), unique_epilogues=len({d for _,d,_,_ in hits}),
                          with_tls=sum(shape[0] for *_,shape in hits),
                          canary_sources=Counter(shape[1] for *_,shape in hits),
                          failure_targets=len({shape[-1] for *_,shape in hits})), sort_keys=True))


if __name__ == '__main__':
    main()
