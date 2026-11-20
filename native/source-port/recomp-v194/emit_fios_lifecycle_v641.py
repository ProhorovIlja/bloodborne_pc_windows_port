# SPDX-License-Identifier: GPL-2.0-or-later
"""Lower two pinned Fios file-object methods into private native C."""
from hashlib import sha256
from struct import unpack_from

NS = ('libSceFios2', 257), ('libSceFios2', 1)
METHODS = (
    (0x457cd0, 0xb0, '08f7ab37e3740807fcb67230845ba7257ec2851fc6ac8b05aefd5751ea0a3bbd', 0x49, 'b44anV2D7K0'),
    (0x457db0, 0x2b, 'e76c137b5c330546528a9c7bb7a27db0563109a264e74bd2ebe4391fe4b72c22', 0x18, 'AOujSGqU+ms'),
)


def emit(read, imports):
    for entry, size, digest, call, nid in METHODS:
        body = read(entry, size)
        if sha256(body).hexdigest() != digest or body[call] != 0xe8:
            raise ValueError('unexpected Fios method')
        plt = entry + call + 5 + unpack_from('<i', body, call + 1)[0]
        stub = read(plt, 6)
        if len(stub) != 6 or stub[:2] != b'\xff\x25':
            raise ValueError('unexpected PLT stub')
        slot = plt + 6 + unpack_from('<i', stub, 2)[0]
        if imports.get((nid, *NS)) != [(slot, 7, 0)]:
            raise ValueError('unexpected Fios import binding')
    return '''/* Private native output; do not distribute. */
#include <stdint.h>
#include <string.h>
_Static_assert(sizeof(uintptr_t) == 8, "64-bit native address point required");
/* The caller supplies its native address point and an infallible allocator,
 * matching this original method's allocation contract. No guest TLS or vtable. */
unsigned char *bb_fios_open_v641(const char *path, uint16_t flags,
        uintptr_t address_point, void *(*allocate)(size_t),
        int32_t (*open_fh)(const void *, int32_t *, const char *, const void *)) {
    _Alignas(8) unsigned char params[24] = {0};
    int32_t id = -1;
    memcpy(params, &flags, 2);
    if (open_fh(NULL, &id, path, params)) return NULL;
    unsigned char *o = allocate(24);
    const uint32_t header = UINT32_C(0xffff0001);
    memcpy(o, &address_point, 8);
    memcpy(o + 8, &header, 4);
    memcpy(o + 12, &id, 4);
    o[16] = 1;
    return o;
}

void bb_fios_close_v641(unsigned char o[static 17],
        int32_t (*close_fh)(const void *, int32_t)) {
    int32_t id;
    memcpy(&id, o + 12, 4);
    if (id < 0 || !o[16]) return;
    (void)close_fh(NULL, id);
    id = -1;
    memcpy(o + 12, &id, 4);
}
'''


def main():
    import argparse
    from pathlib import Path
    from audit_modules_v628 import PINS, file_reader, link_tables
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    a = p.parse_args()
    data = a.eboot.read_bytes()
    if sha256(data).hexdigest() != PINS[0]:
        p.error('unsupported eboot hash')
    details = {}
    link_tables(data, details=details)
    ph, file = file_reader(data)

    def read(va, size):
        (seg,) = (s for s in ph if s[0] == 1 and s[1] & 1 and s[3] <= va <= s[3] + s[5] - size)
        return file(seg[2] + va - seg[3], size)

    print(emit(read, details['imports']), end='')


if __name__ == '__main__':
    main()
