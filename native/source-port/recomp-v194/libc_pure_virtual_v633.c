/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/* A pure-virtual call is a fatal error, not an unimplemented game call.
 * The PS4 wrapper forwards the reason to the kernel debug exception import.
 * Use host termination, not the original PRX or the host C++ ABI symbol. */
typedef void (*BbPureVirtualTarget633)(void);

static _Noreturn void bb_pure_virtual_v633(void) {
    fputs("Bloodborne: pure virtual call (PS4 error 0xa002000a)\n", stderr);
    abort();
}

BbPureVirtualTarget633 bb_libc_pure_virtual_resolve_v633(const char *nid,
        const char *module, unsigned mv, const char *library, unsigned lv,
        unsigned elf_type) {
    if (!nid || !module || !library || mv != 0x101 || lv != 1 || elf_type != 2 ||
        strcmp(module, "libc") || strcmp(library, "libc") || strcmp(nid, "zr094EQ39Ww"))
        return NULL;
    return bb_pure_virtual_v633;
}
