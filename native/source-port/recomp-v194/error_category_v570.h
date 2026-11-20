/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ERROR_CATEGORY_V570_H
#define BB_ERROR_CATEGORY_V570_H
#include <stdint.h>

/* Model of the three error categories published before constructor 90.
 * Use stable native object identities, never the host std::error_category ABI.
 * This pair describes values, not the ABI for returning them on Win64. */
struct bb_error_value_v570 { uint64_t word, category; };
struct bb_error_categories_v570 { uint64_t system, generic, iostream; };
typedef int (*bb_error_known_v570)(void *, int32_t);

static inline const char *bb_error_name_v570(
    struct bb_error_categories_v570 c, uint64_t self) {
    if (!self) return 0;
    return self==c.system ? "system" : self==c.generic ? "generic" :
           self==c.iostream ? "iostream" : 0;
}

/* The original tests _Syserror_map(code) for non-null. This policy must
 * describe the PS4 error domain, not host errno or Win32 last-error. */
static inline int bb_error_default_v570(struct bb_error_categories_v570 c,
    uint64_t self, int32_t code, bb_error_known_v570 known, void *ctx,
    struct bb_error_value_v570 *out) {
    if (!out || !bb_error_name_v570(c,self) || !c.generic ||
        !c.system || !c.iostream || c.system==c.generic ||
        c.system==c.iostream || c.generic==c.iostream ||
        (self==c.system && !known)) return 0;
    const uint64_t cat=self==c.system && known(ctx,code) ? c.generic : self;
    *out=(struct bb_error_value_v570){(uint64_t)(uint32_t)code<<32,cat};
    return 1;
}

static inline int bb_error_equal_v570(struct bb_error_value_v570 a,
    struct bb_error_value_v570 b) {
    return a.category==b.category && a.word>>32==b.word>>32;
}
#endif
