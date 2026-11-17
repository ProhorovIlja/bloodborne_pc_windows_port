/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_CONTROL_V588_H
#define BB_ARENA_CONTROL_V588_H
#include <cstdint>

struct BbMutexControlV588 {
    void *context;
    bool (*ready)(void *);
    uint32_t (*lock)(void *);
    uint32_t (*unlock)(void *);
    void (*diagnostic)(void *,unsigned);
};
enum class BbControlStateV588 { complete, invalid };
struct BbControlResultV588 { BbControlStateV588 state; int32_t value; };
/* Typed adapter for translated callers. Callback results are Orbis status
 * bits, not host errno. If diagnostic returns, preserve retail continuation.
 * A host integration may instead make diagnostic terminal. */
static inline BbControlResultV588 bb_arena_control_v588(unsigned slot,
    const BbMutexControlV588 *m=nullptr) {
    using S=BbControlStateV588;
    switch (slot) {
    case 0x00: case 0x78: case 0xb8: return {S::complete,0};
    case 0x18: return {S::complete,-1};
    case 0xc0: case 0xc8: break;
    default: return {S::invalid,0};
    }
    const bool attempt=slot==0xc0;
    if (!m || !m->ready || !m->diagnostic || !(attempt?m->lock:m->unlock))
        return {S::invalid,0};
    if (!m->ready(m->context)) m->diagnostic(m->context,attempt?0x7e:0x99);
    const uint32_t rc=(attempt?m->lock:m->unlock)(m->context);
    if (!rc) return {S::complete,0};
    if (!attempt) {
        if (rc!=0x80020001u) m->diagnostic(m->context,rc==0x80020016u?0xc0:0xc5);
        return {S::complete,0};
    }
    switch (rc) {
    case 0x8002003cu: return {S::complete,-3};
    case 0x8002000bu: m->diagnostic(m->context,0x80); [[fallthrough]];
    case 0x80020016u: m->diagnostic(m->context,0x82); [[fallthrough]];
    case 0x80020023u: m->diagnostic(m->context,0x84); [[fallthrough]];
    default: m->diagnostic(m->context,0x86); return {S::complete,0};
    }
}
#endif
