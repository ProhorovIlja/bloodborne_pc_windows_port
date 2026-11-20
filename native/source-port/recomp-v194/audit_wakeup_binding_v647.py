# SPDX-License-Identifier: GPL-2.0-or-later
"""Attest constructor 1's published callback and shared startup storage."""
from hashlib import sha256
from struct import unpack_from


def target(body, base, off, size):
    return base + off + size + unpack_from('<i', body, off + size - 4)[0]


def audit(read, first):
    ctor = read(first, 15)
    if ctor[:4] != b'\x53\x48\x8d\x05' or ctor[8:11] != b'\x48\x89\x05':
        raise ValueError('unexpected hook publication')
    hook = target(ctor, first, 1, 7)
    published = target(ctor, first, 8, 7)
    code = read(hook, 0xae)
    if sha256(code).hexdigest() != '4fc8bf41d368aae3c27f44e0d8b13bd3d2e14fcfa61ebade729d7d52ebe80e33':
        raise ValueError('unexpected callback')
    # Compare data references and helper targets rather than assuming that
    # the similarly shaped callback and constructor share one state object.
    full = read(first, 0xd8)
    if sha256(full).hexdigest() != '5fe76d49ac1d0092ed0fb8d3af3c72af94df334927439ee66f4366f84518ced2':
        raise ValueError('unexpected constructor')
    for a, b, size in ((0xf,0x6,6),(0x3c,0x33,6),(0x45,0x3c,7),
                       (0x59,0x50,7),(0x6b,0x62,5),(0x81,0x78,5)):
        if target(full, first, a, size) != target(code, hook, b, size):
            raise ValueError('callback state or helper differs')
    if published + 8 != target(code, hook, 0x3c, 7):
        raise ValueError('unexpected hook storage')
    return {'shared_data_references': 4, 'shared_helper_calls': 2, 'published_callbacks': 1}


def main():
    import argparse
    import json
    from pathlib import Path
    from ps4_ctor_order_v567 import inspect
    from audit_modules_v628 import file_reader
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    blob = p.parse_args().eboot.read_bytes()
    order, _ = inspect(blob)
    ph, read_file = file_reader(blob)

    def read(va, size):
        (seg,) = (s for s in ph if s[0] == 1 and s[1]&1 and s[3] <= va <= s[3]+s[5]-size)
        return bytes(read_file(seg[2]+va-seg[3], size))

    print(json.dumps(audit(read, order[0]), sort_keys=True))


if __name__ == '__main__':
    main()
