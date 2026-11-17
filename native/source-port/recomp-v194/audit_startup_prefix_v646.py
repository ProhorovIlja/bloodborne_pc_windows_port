# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline audit of the first two startup entries and their shared mutex."""
from hashlib import sha256
from struct import unpack_from

PROFILE = (
    (0x20edf90, 0xd8, '5fe76d49ac1d0092ed0fb8d3af3c72af94df334927439ee66f4366f84518ced2'),
    (0x1fc22c0, 5, '40f19afffb3e79c39f5e20ee4545d068afe37db1dec5de1712b7c989ce407ce7'),
    (0x207fa50, 0x13f, '7c10820a0d479279004b45045fb3f9f6a458a0c91845a148b5b1de64803cc7e8'),
    (0x20819f0, 0xd6, 'bd6a69a5ba9d86d2a20ae57415c86ae73787e7e9aa62d26e02eb47de5ac29e3a'),
)
MEMORY = (
    (0x2bbeaa8, 'pO96TwzOm5E', 'sceKernelGetDirectMemorySize'),
    (0x2bbeab8, 'rTXw65xmLIA', 'sceKernelAllocateDirectMemory'),
    (0x2bbeac8, 'L-Q3LEjIbgA', 'sceKernelMapDirectMemory'),
)


def audit(read, order, details):
    if list(order[:2]) != [r[0] for r in PROFILE[:2]]:
        raise ValueError('unexpected startup prefix')
    for va, size, digest in PROFILE:
        if sha256(read(va, size)).hexdigest() != digest:
            raise ValueError('unexpected constructor or arena bytes')
    rel = {slot: (info, addend) for slot, info, addend in details['relocations']}
    mutex = {0x52b6240: 0x207ee80, 0x52b6248: 0x207ee90, 0x52b6258: 0x207f070}
    if any(rel.get(slot) != (8, target) for slot, target in mutex.items()):
        raise ValueError('unexpected mutex virtual routes')
    imports = []
    for plt, nid, name in MEMORY:
        stub = read(plt, 6)
        if stub[:2] != b'\xff\x25' or len(stub) != 6:
            raise ValueError('unexpected PLT stub')
        slot = plt + 6 + unpack_from('<i', stub, 2)[0]
        key = nid, ('libkernel', 257), ('libkernel', 1)
        if details['imports'].get(key) != [(slot, 7, 0)]:
            raise ValueError('unexpected arena import route')
        imports.append(name)
    return {'constructor_entries': 2, 'shared_mutex_slots': len(mutex),
            'arena_imports': imports, 'arena_size': 0x7400000, 'alignment': 0x200000}


def main():
    import argparse
    import json
    from pathlib import Path
    from audit_modules_v628 import file_reader, link_tables
    from ps4_ctor_order_v567 import inspect
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot', type=Path)
    a = parser.parse_args()
    blob = a.eboot.read_bytes()
    order, _ = inspect(blob)
    segments, read_file = file_reader(blob)
    details = {}
    link_tables(blob, details=details)

    def read(va, size):
        (seg,) = (p for p in segments if p[0] == 1 and p[1]&1 and p[3] <= va <= p[3]+p[5]-size)
        return read_file(seg[2]+va-seg[3], size)

    print(json.dumps(audit(read, order, details), sort_keys=True))


if __name__ == '__main__':
    main()
