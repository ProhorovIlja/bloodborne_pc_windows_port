# SPDX-License-Identifier: GPL-2.0-or-later
"""Candidate rel32 dispatches with an adjacent unsigned 32-bit guard; offline only."""
import re
import struct

FORM = re.compile(rb'\x83[\xf8-\xff][\x00-\x7f](?:\x77.|\x0f\x87....)'
                  rb'(?:\x48\x8d\x15....\x48\x63\x0c\x8a\x48\x01\xd1\xff\xe1'
                  rb'|\x4c\x8d\x05....\x49\x63\x3c\xb8\x4c\x01\xc7\xff\xe7)', re.S)


def candidates(rx, base, lo, hi):
    if not 0 <= base <= lo < hi <= base + len(rx) <= 1 << 64:
        raise ValueError('invalid function extent')
    for m in FORM.finditer(rx, lo-base, hi-base):
        code = m[0]
        n = len(code)-16
        start = base+m.start()
        lea = start+n
        index = code[1] & 7
        if index != (1 if code[n] == 0x48 else 7):
            continue
        default = lea+int.from_bytes(code[4 if n == 5 else 5:n], 'little', signed=True)
        table = lea+7+struct.unpack_from('<i', code, n+3)[0]
        end = table+4*(code[2]+1)
        if not base <= table < end <= base+len(rx) or table < lea+16 and start < end:
            continue
        targets = tuple(table+d for (d,) in struct.iter_unpack('<i', rx[table-base:end-base]))
        if any(not lo <= a < hi or table <= a < end or start <= a < lea+16 for a in (default, *targets)):
            continue
        yield start, table, default, targets
