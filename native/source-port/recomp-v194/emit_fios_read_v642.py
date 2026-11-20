# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline lowering of one pinned Fios read method; no runtime game image."""
from hashlib import sha256
from struct import unpack_from

ENTRY = 0x45cf60
SIZE = 0x35
CALL = 0x21
DIGEST = '4f0acb11b29b9125ceb31372f3bc775477cd43df37e4f4df0180dfb2c027f565'
KEY = ('Bn2ZF4ZjeuQ', ('libSceFios2', 257), ('libSceFios2', 1))


def emit(read, imports):
    body = read(ENTRY, SIZE)
    if sha256(body).hexdigest() != DIGEST or body[CALL] != 0xe8:
        raise ValueError('unexpected Fios read method')
    plt = ENTRY + CALL + 5 + unpack_from('<i', body, CALL + 1)[0]
    stub = read(plt, 6)
    if len(stub) != 6 or stub[:2] != b'\xff\x25':
        raise ValueError('unexpected PLT stub')
    slot = plt + 6 + unpack_from('<i', stub, 2)[0]
    if imports.get(KEY) != [(slot, 7, 0)]:
        raise ValueError('unexpected Fios import binding')
    return '''/* Private native output; do not distribute. */
#include <stdint.h>
#include <string.h>
int32_t bb_fios_read_v642(unsigned char o[static 17], void *buf, int32_t n,
        int64_t (*read_fh)(const void *, int32_t, void *, int64_t)) {
    int32_t id, result;
    memcpy(&id, o + 12, 4);
    if (id < 0 || !n || !read_fh) return 0;
    uint32_t low = (uint32_t)read_fh(NULL, id, buf, n);
    memcpy(&result, &low, 4);
    if (result <= 0) o[16] = 0;
    return result;
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
