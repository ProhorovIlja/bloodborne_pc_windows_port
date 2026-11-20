# SPDX-License-Identifier: GPL-2.0-or-later
"""Classify offline RX relocations without assuming that RX means function.

Only emit counts. Reuse V712 FDE validation, V711 switch decoding and
V719 input attestation. FDE interior/gap are not runtime target types.
"""
import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from audit_eboot_pair_v719 import ELF_SHA, PH, SELF_SHA, audit, require, span
from audit_switch_flow_v714 import extents, scan


def classify(elf):
    ph = list(PH.iter_unpack(span(elf, 64, 10*PH.size)))
    rx, rw, dyn, eh, meta = (ph[i] for i in (0, 1, 3, 6, 7))
    require(eh[0] == 0x6474e550 and rx[0] == rw[0] == 1, 'unexpected segments')
    base = rx[3]
    code = bytes(span(elf, rx[2], rx[5]))
    ranges, unwind = extents(code, base, eh[3]-base, eh[5])
    require(all(a[1] <= b[0] for a,b in zip(ranges,ranges[1:])), 'ambiguous FDE')
    starts = [a for a,_ in ranges]
    cases = {t for _,_,targets,default in scan(code,base) for t in (*targets,default)}
    tags = dict(iter_unpack('<2Q', span(elf,dyn[2],dyn[5])))
    jump = span(elf,meta[2]+tags[0x61000029],tags[0x6100002d])
    slots = {dst for dst, info, _ in iter_unpack('<QQq',jump) if info & 0xffffffff == 7}
    rels = span(elf,meta[2]+tags[0x6100002f],tags[0x61000031])
    counts, unique, seen = Counter(), {}, set()
    for dst,info,t in iter_unpack('<QQq',rels):
        if info != 8 or not base <= t < base+rx[6]:
            continue
        require(rw[3] <= dst <= rw[3]+rw[6]-8 and dst not in seen, 'invalid or duplicate RX pointer slot')
        seen.add(dst)
        i = bisect_right(starts,t)-1
        o = t-base
        # Recognize only an exact RIP-relative jump to a known JUMP_SLOT.
        if i >= 0 and t == ranges[i][0]:
            kind = 'fde_entry'
        elif t in cases:
            kind = 'bounded_switch_target'
        elif code[o:o+2] == b'\xff\x25' and o+6 <= len(code) and t+6+unpack_from('<i',code,o+2)[0] in slots:
            kind = 'jump_slot_stub_candidate'
        elif i >= 0 and t < ranges[i][1]:
            kind = 'fde_interior_unclassified'
        elif ranges[-1][1] <= t < base+unwind:
            kind = "post_fde_pre_unwind_unclassified"
        else:
            kind = 'outside_fde_unclassified'
        unique[t] = kind
        counts[kind] += 1
    require(sum(counts.values()) == len(seen), 'incomplete classification')
    return {'slots': dict(counts), 'distinct_targets': dict(Counter(unique.values()))}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('self',type=Path)
    p.add_argument('elf',type=Path)
    a = p.parse_args()
    require((a.self.stat().st_size,a.elf.stat().st_size) == (93825704,93667640), 'unexpected input size')
    s,e = a.self.read_bytes(),a.elf.read_bytes()
    require(sha256(s).hexdigest() == SELF_SHA and sha256(e).hexdigest() == ELF_SHA, 'unexpected input identity')
    counts = audit(s,e)
    result = classify(e)
    require(sum(result['slots'].values()) == counts['relative_rw_to_rx'], 'V719 total mismatch')
    print(json.dumps(result,sort_keys=True))
