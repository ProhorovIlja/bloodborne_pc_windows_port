/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RESUME_RESTORE_V700_H
#define BB_RESUME_RESTORE_V700_H
#include "resume_profile_return_v696.h"

static inline void bb_profile_switch700(unsigned char *p, uint64_t now) {
    uint32_t count;
    memcpy(&count,p+0x4e8,4);
    ++count;
    memcpy(p+0x4e8,&count,4);
    bb_profile_put695(p,0x4c0,bb_profile_get695(p,0x4c0)+now-bb_profile_get695(p,0x4b8));
    bb_profile_put695(p,0x4b8,now);
}

/* Nonzero only. Caller resolves parent (vm+0x90), current (vm+0x10)
 * and previous (R15); the two profile buffers may be identical. All
 * other spans and the frame/state are disjoint. */
static inline enum bb_profile_result696 bb_resume_restore700(
        struct bb_profile_state696 *s, uint32_t value,
        unsigned char *vm, size_t vs, const unsigned char *parent, size_t ts,
        unsigned char *current, size_t cs, unsigned char *previous, size_t ps,
        uint64_t first, uint64_t second, const uint64_t *f, size_t n, uint64_t guard) {
    if (!s || s->pc!=UINT64_C(0x25cdd02) || !value || !vm || vs<0xc8 ||
        !parent || ts<0x68 || !current || cs<0x4ec || !previous || ps<0x4ec ||
        !f || n<26) return BB_PROFILE_MISS;
    bb_profile_put695(vm,0x90,bb_profile_get695(parent,0x60));
    bb_profile_put695(current,0x4a8,s->nv[3]-1);
    bb_profile_put695(current,0x4b0,f[3]);
    bb_profile_switch700(current,first);
    bb_profile_switch700(previous,second);
    bb_profile_put695(previous,0x4a8,bb_profile_get695(previous,0x4a8)+1);
    bb_profile_put695(previous,0x4b0,f[3]);
    memcpy(vm+0xc4,(const unsigned char *)f+0x24,4);
    if (f[18]!=guard) {
        s->pc=UINT64_C(0x2bbe4f8); s->rax=guard; s->used=0;
        s->nv[3]--; s->nv[4]=value;
        return BB_PROFILE_FATAL;
    }
    const unsigned order[]={0,2,3,4,5,1};
    for (size_t i=0;i<6;i++) s->nv[order[i]]=f[19+i];
    s->pc=f[25]; s->rax=value; s->used=26;
    return BB_PROFILE_RET;
}
#endif
