# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline writable/TLS templates; no executable segments copied."""
from collections import namedtuple

Layout = namedtuple('Layout', 'base template size tls_template tls_size tls_align')


def prepare(image, loads, tls, slots):
    """ELF64 program-header rows and normalized, independently parsed RELA slots.

    Deliberately supports the single RW LOAD profile. Reject ambiguous layouts.
    Caller authenticates the image and performs the complete V466/V467 checks.
    """
    if len(loads) != 2 or sorted(row[1] for row in loads) != [5, 6]:
        raise ValueError('unsupported LOAD profile')
    spans = []
    for kind, flags, off, va, _, files, mem, align in loads:
        if (kind != 1 or not 0 < mem <= 268435456 or not 0 <= files <= mem
                or not 0 <= off <= len(image)-files or not 0 <= va <= 2**64-mem
                or align <= 0 or align & (align-1) or (va-off) % align):
            raise ValueError('invalid LOAD')
        spans.append((va, va+mem))
        if flags == 6:
            start, rw_off, rw_files, rw_size = va, off, files, mem
    a, b = sorted(spans)
    if a[1] > b[0]:
        raise ValueError('overlapping LOADs')
    kind, flags, off, va, _, files, mem, align = tls
    if (kind != 7 or flags != 4 or not 0 <= files <= mem <= 1048576
            or not 0 < align <= 65536 or align & (align-1) or va % align
            or not start <= va <= start+rw_size-mem
            or off != rw_off+va-start or not 0 <= off <= len(image)-files
            or (files and va+files > start+rw_files)):
        raise ValueError('invalid TLS layout')
    raw = bytearray(image[rw_off:rw_off+rw_files])
    end = start
    for slot in sorted(slots):
        if not end <= slot <= start+rw_size-8 or (va < slot+8 and slot < va+mem):
            raise ValueError('invalid, overlapping or TLS relocation')
        end = slot+8
        lo = slot-start
        if lo < rw_files:
            n = min(8,rw_files-lo)
            raw[lo:lo+n] = bytes(n)
    return Layout(start, bytes(raw), rw_size, bytes(image[off:off+files]), mem, align)
