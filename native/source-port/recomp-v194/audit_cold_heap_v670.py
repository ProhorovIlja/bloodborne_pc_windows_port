# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline audit of the cold dependency helper reached by constructor 90."""
import argparse
import json
from hashlib import sha256
from pathlib import Path
from struct import unpack_from

from audit_ctor90_v648 import SIZE, audit as audit_prefix, refs
from audit_modules_v628 import file_reader, link_tables
from ps4_ctor_order_v567 import inspect


def audit_dependency(read, helper, reloc):
    body = read(helper, 0x3e7)
    if sha256(body).hexdigest() != 'd5d71fe2e603f28d3e30a44b2fe1878821e8ab2e7fe464a18139613ae789f4ac':
        raise ValueError('unexpected cold dependency helper')
    def rip(site, prefix):
        if not body.startswith(prefix, site):
            raise ValueError(f'unexpected opcode at helper+{site:#x}')
        disp = site + len(prefix)
        return helper + disp + 4 + unpack_from('<i', body, disp)[0]
    def call(site):
        return rip(site, b'\xe8')
    def slot(table, offset):
        kind, target = reloc[table + offset]
        if kind != 8:
            raise ValueError(f'expected relative relocation at {table + offset:#x}')
        read(target, 1)
        return target

    outer = rip(0x6b, b'\x48\x8d\x05') + 16
    primary = rip(0x126, b'\x48\x8d\x05')
    secondary = rip(0x16a, b'\x48\x8d\x05') + 16
    view = rip(0x13e, b'\x48\x8d\x05')
    outer_enter, outer_leave = slot(outer, 0x18), slot(outer, 0x28)
    if (outer_enter, outer_leave) != (slot(primary, 0x18), slot(primary, 0x28)):
        raise ValueError('expected shared recursive lock methods, on distinct instances')
    return dict(helper=helper, cold_steps=[
        ['outer_mutex_init', call(0x93)],
        ['outer_mutex_enter', outer_enter],
        ['secondary_rwlock_init', call(0x185)],
        ['outer_mutex_leave', outer_leave],
        ['locked_heap_activate', call(0x1e2)],
        ['view_allocate_header', slot(view, 0x58)],
        ['primary_mutex_enter', slot(primary, 0x18)],
        ['plain_allocate_records', call(0x297)],
        ['primary_mutex_leave', slot(primary, 0x28)],
        ['register_backing_range', call(0x3d0)],
    ], secondary_ready=slot(secondary, 0x10))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    blob = p.parse_args().eboot.read_bytes()
    order, _ = inspect(blob)
    ph, file = file_reader(blob)
    details = {}
    link_tables(blob, details=details)

    def read(va, size):
        (segment,) = (s for s in ph if s[0] == 1 and s[1] & 1
                      and s[3] <= va <= s[3] + s[5] - size)
        return bytes(file(segment[2] + va - segment[3], size))

    reloc = {s: (t, a) for s, t, a in details['relocations']}
    audit_prefix(read, order, reloc)
    ctor = order[89]
    helper = refs(ctor, read(ctor, SIZE))[-1]
    print(json.dumps(audit_dependency(read, helper, reloc), indent=2))


if __name__ == '__main__':
    main()
