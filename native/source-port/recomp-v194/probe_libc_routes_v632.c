/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "libc_provider_v631.c"
#include <stdio.h>

int main(void) {
    const unsigned mv = 0x101, lv = 1;
    for (size_t i = 0; i < sizeof routes631 / sizeof *routes631; ++i) {
        const BbLibcRoute631 *r = routes631 + i;
        if (bb_libc_resolve_v631(r->nid, "libc", mv, "libc", lv, 2, r->signature) != r ||
            bb_libc_resolve_v631(r->nid, "libc", mv, "libc", lv, 1, r->signature)) return 1;
        if (printf("%s\tlibc\t%u\tlibc\t%u\n", r->nid, mv, lv) < 0) return 1;
    }
    return fflush(stdout) == EOF;
}
