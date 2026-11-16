# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline check for normalized SCE 64-bit relocation records, not a loader."""
from bisect import bisect_right
from collections import Counter

LIMIT = 1 << 64


def audit(loads, relocations, slides):
    # loads: (guest_start, file_bytes, memory_bytes, ELF flags)
    # relocations: (guest_slot, ELF r_info, signed addend)
    loads = sorted(loads)
    if not loads or len(loads) > 256 or len(slides) != 2 or slides[0] == slides[1]:
        raise ValueError('invalid layout or slides')
    starts = [row[0] for row in loads]
    end = 0
    for start, file_size, mem_size, flags in loads:
        if not (end <= start < LIMIT and 0 <= file_size <= mem_size and
                0 < mem_size <= LIMIT-start and flags in (4, 5, 6)):
            raise ValueError('invalid load')
        end = start + mem_size
    if any(s < 0 or s & 4095 or s > LIMIT-end for s in slides):
        raise ValueError('invalid slide')

    def segment(addr, width):
        i = bisect_right(starts, addr)-1
        if i < 0 or addr+width > loads[i][0]+loads[i][2]:
            raise ValueError('unmapped relocation span')
        return loads[i]

    counts = Counter()
    end = 0
    for slot, info, addend in sorted(relocations):
        if slot < end:
            raise ValueError('overlapping relocations')
        end = slot+8
        start, file_size, _, flags = segment(slot, 8)
        if flags != 6:
            raise ValueError('relocation destination is not writable data')
        counts['file_slots' if end <= start+file_size else 'zero_tail_slots'] += 1
        kind = info & 0xffffffff
        if kind in (1, 6, 7) and 0 < info < LIMIT and info >> 32:
            counts['symbol_type_'+str(kind)] += 1
            continue
        if info != 8:
            raise ValueError('unsupported relocation')
        start, file_size, _, flags = segment(addend, 1)
        counts['relative_rx_segment' if flags == 5 else
               'relative_file_data' if addend < start+file_size else 'relative_zero_tail'] += 1
        for slide in slides:
            if int.from_bytes((slide+addend).to_bytes(8, 'little'), 'little')-slide != addend:
                raise ValueError('invalid normalized pointer')
    return dict(sorted(counts.items()))


def self_test():
    loads = [(0, 256, 256, 5), (4096, 32, 64, 6)]
    slides = [0x400000, 0x100000000]
    rel = [(4096, 8, 0), (4104, 8, 4104), (4112, 8, 4140), (4128, (3<<32)+7, 0)]
    assert audit(loads, rel, slides) == dict(file_slots=3, zero_tail_slots=1,
        relative_rx_segment=1, relative_file_data=1, relative_zero_tail=1, symbol_type_7=1)
    for bad in ([(0,8,0)], [(4096,8,256)], [(4096,8,-1)], [(4155,8,0)],
                [(4097,8,0),(4104,8,0)], [(4096,(1<<32)+8,0)], [(4096,7,0)]):
        try:
            audit(loads, bad, slides)
        except ValueError:
            continue
        raise AssertionError('invalid relocation accepted')
    for bad in ([0,0], [0,1], [0,LIMIT], [-4096,0]):
        try:
            audit(loads, rel, bad)
        except ValueError:
            continue
        raise AssertionError('invalid slide accepted')
    print('NATIVE_V466_REBASE_AUDIT_PASS')


if __name__ == '__main__':
    self_test()
