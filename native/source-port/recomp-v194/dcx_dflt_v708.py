# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline DCX DFLT reader. Layout checked against SoulsFormats Formats/DCX.cs.

This is a strict reader for five documented DFLT variants, not a generic
DCX parser. No guest code is loaded. Callers bound the input before reading.
"""
from struct import Struct
import zlib

HEADER = Struct('>4s5I4sII4s4s6I4sI')
VARIANTS = {(0x10000, 0x24, 9, 0), (0x10000, 0x44, 9, 0),
            (0x11000, 0x44, 8, 0), (0x11000, 0x44, 9, 0),
            (0x11000, 0x44, 9, 15)}


def unpack(data, *, max_output):
    if not 0 <= max_output <= 0x7fffffff or len(data) < HEADER.size:
        raise ValueError('invalid limit or short header')
    (dcx, version, a, b, kind, end, dcs, size, stored, dcp, codec,
     head, level, zero1, flags, zero2, tag, dca, tail) = HEADER.unpack_from(data)
    if (dcx, dcs, dcp, codec, dca) != (b'DCX\0', b'DCS\0', b'DCP\0', b'DFLT', b'DCA\0'):
        raise ValueError('not DCX DFLT')
    if ((version, kind, level >> 24, flags >> 24) not in VARIANTS or
            (a, b, end, head, zero1, zero2, tag, tail) != (24, 36, kind+8, 32, 0, 0, 0x10100, 8) or
            (level | flags) & 0xffffff):
        raise ValueError('unsupported DFLT layout')
    if size > max_output or stored != len(data)-HEADER.size:
        raise ValueError('invalid compressed span or output size')
    decoder = zlib.decompressobj()
    try:
        out = decoder.decompress(memoryview(data)[HEADER.size:], size+1)
    except zlib.error as exc:
        raise ValueError('invalid zlib stream') from exc
    if len(out) != size or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('incomplete stream, trailing bytes or size mismatch')
    return out
