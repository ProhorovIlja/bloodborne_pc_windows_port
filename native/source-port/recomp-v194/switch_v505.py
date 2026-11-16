# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline conversion of a pre-classified rel32 switch table to native route IDs."""
import struct

LIMIT = 1 << 64


def plan(raw, base, allowed):
    """Caller proves table extent, offset base, and destination semantics first."""
    if type(base) is not int or not 0 <= base < LIMIT or not 0 < len(raw) <= 16384 or len(raw) % 4:
        raise ValueError('invalid switch table')
    destinations = tuple(base + d for (d,) in struct.iter_unpack('<i', raw))
    if any(not 0 <= a < LIMIT or a not in allowed for a in destinations):
        raise ValueError('unknown native switch destination')
    return destinations


def emit(destinations):
    if not 0 < len(destinations) <= 4096 or any(type(a) is not int or not 0 <= a < LIMIT for a in destinations):
        raise ValueError('invalid native route IDs')
    rows = ','.join(f'UINT64_C({a})' for a in destinations)
    return ('#include <stddef.h>\n#include <stdint.h>\n'
            'static int switch_route(size_t i,uint64_t *out) {\n'
            f' static const uint64_t ids[]={{{rows}}};\n'
            ' if(!out || i>=sizeof ids/sizeof *ids)return 0;\n'
            ' *out=ids[i];return 1;\n}\n')
