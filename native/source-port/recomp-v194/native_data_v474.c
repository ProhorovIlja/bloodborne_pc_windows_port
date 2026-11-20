/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct bb_patch_v474 { size_t offset; uint64_t value; };
/* Inputs must not alias dst. Values are guest IDs/addresses, not host pointers.
 * Only the owner-local builder may supply the attested template and bindings. */
int bb_data_init_v474(unsigned char *dst, size_t dn, const unsigned char *src,
    size_t sn, const struct bb_patch_v474 *patch, size_t count) {
    if (!dst || !dn || dn > 268435456 || sn > dn || (sn && !src) ||
        count > 2000000 || (count && (!patch || dn < 8))) return 0;
    size_t end = 0;
    for (size_t i=0; i<count; ++i) {
        size_t o=patch[i].offset;
        if (o<end || o>dn-8) return 0;
        /* The offline template must not keep stale loader pointers. */
        for (size_t j=0; j<8 && o+j<sn; ++j)
            if (src[o+j]) return 0;
        end=o+8;
    }
    if (sn) memcpy(dst,src,sn);
    memset(dst+sn,0,dn-sn);
    for (size_t i=0; i<count; ++i)
        for (unsigned j=0; j<8; ++j)
            dst[patch[i].offset+j]=(unsigned char)(patch[i].value>>(8*j));
    return 1;
}
