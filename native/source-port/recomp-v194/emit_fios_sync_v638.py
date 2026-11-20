# SPDX-License-Identifier: GPL-2.0-or-later
"""Emit one attested Fios2 sync caller. Original code is never a runtime input."""
import hashlib
import struct

KEY = ('EzzSJz6yuMc', ('libSceFios2', 257), ('libSceFios2', 1))
ENTRY = 0x457f80
LEAF_HASH = '7fe2cff6fde3009d3c0e87e7d552632a16e790b6669847c581702e1acca45370'


def emit(read, sites):
    if len(sites) != 1 or sites[0][1:] != (7, 0):
        raise ValueError('wrong Fios2 import relocation')
    body = read(ENTRY, 15)
    if hashlib.sha256(body).hexdigest() != LEAF_HASH:
        raise ValueError('wrong sync caller')
    plt = ENTRY + 14 + struct.unpack_from('<i', body, 10)[0]
    stub = read(plt, 6)
    if len(stub) != 6 or stub[:2] != b'\xff\x25' or (
            plt + 6 + struct.unpack_from('<i', stub, 2)[0] != sites[0][0]):
        raise ValueError('sync caller target does not match import')
    return '''/* Private native output; do not distribute. */
#include <stdint.h>
#include <string.h>
/* Returns whether the original void-style caller forwarded the request. */
int bb_fios_forward_sync_v638(const unsigned char object[static 16],
                              int32_t (*sync)(const void *, int32_t)) {
    int32_t handle;
    memcpy(&handle, object + 12, sizeof handle);
    if (handle < 0 || !sync) return 0;
    (void)sync(NULL, handle);
    return 1;
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
    if hashlib.sha256(data).hexdigest() != PINS[0]:
        p.error('unsupported eboot hash')
    details = {}
    link_tables(data, details=details)
    ph, read_file = file_reader(data)

    def read(va, size):
        (seg,) = (s for s in ph if s[0] == 1 and s[1] & 1 and s[3] <= va <= s[3] + s[5] - size)
        return read_file(seg[2] + va - seg[3], size)

    print(emit(read, details['imports'][KEY]), end='')


if __name__ == '__main__':
    main()
