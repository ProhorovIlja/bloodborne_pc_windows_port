/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CONTINUATION_V515_H
#define BB_CONTINUATION_V515_H
#include "jump_record_v514.h"

/* Trusted AOT dispatcher owns this stack and supplies a non-reused activation
 * token per live frame. Calls are serialized within a single guest thread. */
struct bb_frame_v515 { uint64_t token, pc, sp; };
struct bb_stack_v515 { const struct bb_frame_v515 *frames; size_t depth; };

static inline int bb_resume_v515(struct bb_stack_v515 *stack, uint64_t token,
        const unsigned char *record, size_t size, uint64_t value,
        uint32_t mxcsr, uint32_t mask, struct bb_jump_v514 *out) {
    struct bb_jump_v514 next;
    if (!stack || !stack->frames || !token || !out || !stack->depth || stack->depth>4096 ||
        !bb_jump_plan_v514(record,size,value,mxcsr,mask,&next)) return 0;
    size_t found=0;
    for (size_t i=0;i<stack->depth;++i) {
        if (stack->frames[i].token!=token) continue;
        if (found || stack->frames[i].pc!=next.rip || stack->frames[i].sp!=next.rsp) return 0;
        found=i+1;
    }
    if (!found) return 0;
    *out=next;
    stack->depth=found;
    return 1;
}
#endif
