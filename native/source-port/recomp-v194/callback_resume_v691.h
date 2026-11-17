/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CALLBACK_RESUME_V691_H
#define BB_CALLBACK_RESUME_V691_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef void (*bb_error_v691)(uint32_t);
typedef void (*bb_finish_v691)(void *, uint64_t);
struct bb_calls_v691 {
    void *ctx;
    bb_error_v691 (*error)(void *, uint64_t);
    bb_finish_v691 (*finish)(void *, uint64_t, size_t);
};
struct bb_callback_edge_v691 { unsigned extended; };
const struct bb_callback_edge_v691 *bb_callback_lookup_v691(uint64_t);
struct bb_callback_state_v691 { uint64_t pc, nv[6], rax; size_t used; };
enum bb_callback_result_v691 { BB_CALLBACK_MISS, BB_CALLBACK_RET, BB_CALLBACK_STOP };

/* The callbacks may mutate the object but not the frame/state or their own
 * lifetime. STOP is terminal: the first callback has already executed and
 * the newly read finalizer could not be resolved. Do not retry that edge. */
static inline enum bb_callback_result_v691 bb_callback_resume_v691(
    struct bb_callback_state_v691 *s, uint32_t value, void *object, size_t size,
    const struct bb_calls_v691 *calls, const uint64_t *frame, size_t words) {
    if (!s || !value || !object || size < 0x3c || !calls || !calls->finish || !frame)
        return BB_CALLBACK_MISS;
    const struct bb_callback_edge_v691 *edge = bb_callback_lookup_v691(s->pc);
    if (!edge) return BB_CALLBACK_MISS;
    const unsigned wide[] = {0,2,3,4,5,1}, narrow[] = {0,4,5,1};
    const unsigned *pops = edge->extended ? wide : narrow;
    size_t n = edge->extended ? 6 : 4;
    if (words < n+2) return BB_CALLBACK_MISS;
    unsigned char *p = object;
    uint64_t token, table;
    uint32_t status;
    memcpy(&token,p+0x30,sizeof token);
    memcpy(&status,p+0x38,sizeof status);
    if (token && status) {
        bb_error_v691 error = calls->error ? calls->error(calls->ctx,token) : NULL;
        if (!error) return BB_CALLBACK_MISS;
        error(status);
    }
    memcpy(&table,p,sizeof table);
    bb_finish_v691 finish = table ? calls->finish(calls->ctx,table,8) : NULL;
    if (!finish) return token && status ? BB_CALLBACK_STOP : BB_CALLBACK_MISS;
    finish(object,s->nv[4]);
    memcpy(&status,p+0x38,sizeof status);
    s->rax = status;
    for (size_t i=0;i<n;++i) s->nv[pops[i]]=frame[1+i];
    s->pc=frame[n+1];
    s->used=n+2;
    return BB_CALLBACK_RET;
}
#endif
