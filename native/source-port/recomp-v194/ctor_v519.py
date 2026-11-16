# SPDX-License-Identifier: GPL-2.0-or-later
"""Extract an exact guarded data-initializer leaf, not a general x86 lifter."""
import re
import struct

SHAPE = re.compile(rb'\x48\x8d\x05(.{4})\x80\x38\x00\x75\x1c'
                   rb'\x48\x8d\x0d(.{4})\x48\x83\xc1\x10'
                   rb'\x48\x8d\x15(.{4})\x48\x89\x0a\x48\xc7\x00\x01\x00\x00\x00\xc3', re.S)


def extract(raw, pc, rw_base, rw_size, image_limit):
    m = SHAPE.fullmatch(raw)
    if not m:
        return None
    guard, value, dst = (pc+n+struct.unpack('<i', b)[0]
                         for n, b in zip((7, 35, 30), m.groups(), strict=True))
    if (not 0 <= rw_base <= rw_base+rw_size <= image_limit <= 1 << 64
            or not rw_base <= guard <= rw_base+rw_size-8
            or not rw_base <= dst <= rw_base+rw_size-8
            or abs(dst-guard) < 8 or not 0 <= value < image_limit):
        raise ValueError('invalid initializer address')
    return guard-rw_base, dst-rw_base, value
