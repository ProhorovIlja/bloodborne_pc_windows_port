/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLEANUP_RESUME_V688_H
#define BB_CLEANUP_RESUME_V688_H
#include "cleanup_v687.h"

struct bb_cleanup_edge_v688 {
    uint64_t pc, next;
    unsigned embedded, result_in_r14;
};
const struct bb_cleanup_edge_v688 *bb_cleanup_lookup_v688(uint64_t pc);

/* Executes the nonzero continuation through its first JMP. Does not
 * execute the destination (which can include a stack guard and RET). */
static inline int bb_cleanup_resume_v688(uint64_t pc, uint32_t value,
        void *object, size_t size, void *ctx, bb_cleanup_resolve_v687 resolve,
        uint64_t *next, uint64_t *r14, uint32_t *eax, unsigned *eax_defined) {
    if (!object || !value || !next || !r14 || !eax || !eax_defined) return 0;
    const struct bb_cleanup_edge_v688 *edge = bb_cleanup_lookup_v688(pc);
    if (!edge || size < (edge->embedded ? 0x411u : 0x28u)) return 0;
    unsigned char *p = object;
    if (!bb_cleanup_v687(p + (edge->embedded ? 8 : 0),
                         size - (edge->embedded ? 8 : 0), ctx, resolve)) return 0;
    if (edge->embedded) p[0x410] = (p[0x410] & 0xfcu) | 2u;
    *eax_defined = !edge->result_in_r14;
    if (edge->result_in_r14) *r14 = 0;
    else *eax = 0;
    *next = edge->next;
    return 1;
}
#endif
