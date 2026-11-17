# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline lowering of the pinned Fios write wrapper, with explicit error hook."""
from hashlib import sha256
from pathlib import Path
from struct import unpack_from

ENTRY = 0x457e90
SIZE = 0xe2
DIGEST = '43d7746aa54acae6d5c418c9a70f9511102589fe265c899ceec22eb34172350f'
NS = ('libSceFios2', 257), ('libSceFios2', 1)


def emit(read, imports):
    body = read(ENTRY, SIZE)
    if sha256(body).hexdigest() != DIGEST:
        raise ValueError('unexpected write wrapper')
    for off, nid in ((0x3f, 'Kl-TbrDU9YM'), (0xb2, 'AOujSGqU+ms')):
        plt = ENTRY + off + 5 + unpack_from('<i', body, off + 1)[0]
        stub = read(plt, 6)
        if len(stub) != 6 or stub[:2] != b'\xff\x25':
            raise ValueError('unexpected PLT stub')
        slot = plt + 6 + unpack_from('<i', stub, 2)[0]
        if imports.get((nid, *NS)) != [(slot, 7, 0)]:
            raise ValueError('unexpected Fios import binding')
    return '''/* Private native output; do not distribute. */
#include <stdint.h>
#include <string.h>
int32_t bb_fios_write_v640(unsigned char o[static 17], const void *buf, int32_t n,
        int64_t (*write_fh)(const void *, int32_t, const void *, int64_t),
        int32_t (*close_fh)(const void *, int32_t), void (*report)(void)) {
    int32_t id, result;
    if (!write_fh || !close_fh || !report) return 0;
    memcpy(&id, o + 12, 4);
    if (id < 0) return 0;
    uint32_t low = (uint32_t)write_fh(NULL, id, buf, n);
    memcpy(&result, &low, 4);
    if (result > 0) return result;
    if (low == UINT32_C(0x80820015)) report();
    memcpy(&id, o + 12, 4);
    if (id >= 0 && o[16]) {
        (void)close_fh(NULL, id);
        id = -1;
        memcpy(o + 12, &id, 4);
    }
    return result;
}
'''


def main():
    import argparse
    from audit_modules_v628 import PINS, file_reader, link_tables
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot', type=Path)
    args = parser.parse_args()
    data = args.eboot.read_bytes()
    if sha256(data).hexdigest() != PINS[0]:
        parser.error('unsupported eboot hash')
    details = {}
    link_tables(data, details=details)
    ph, file = file_reader(data)

    def read(va, size):
        (seg,) = (s for s in ph if s[0] == 1 and s[1] & 1 and s[3] <= va <= s[3] + s[5] - size)
        return file(seg[2] + va - seg[3], size)

    print(emit(read, details['imports']), end='')


if __name__ == '__main__':
    main()
