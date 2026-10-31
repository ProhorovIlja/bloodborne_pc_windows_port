/* V194 native Windows source-port CPU ABI (GPL-2.0-or-later).
 * Source-locked against bloodborne-native/bloodborne-recomp
 * 8f31ec7c41f252730c6325d52647046baef7549f
 * src/cpu/cpu_internal.h blob bcbd422f92a84087a2e0c2d260ec64040f381540.
 *
 * Windows game-code AOT host structure. No PS4 ELF, EBOOT, compatibility
 * loader or retail bytes are included. This DOES NOT itself boot the game.
 * Never append new upstream fields without updating exact source guard.
 */
#ifndef SHYT_NATIVE_FULL_CPU_ABI_V194_H
#define SHYT_NATIVE_FULL_CPU_ABI_V194_H
#include <stddef.h>
#include <stdint.h>
#include "recomp_abi.h"
#if UINTPTR_MAX != UINT64_MAX
#error "This source-port CPU ABI requires a 64-bit native host"
#endif

typedef union {
    uint8_t b[32];
    int8_t sb[32];
    uint16_t w[16];
    int16_t sw[16];
    uint32_t d[8];
    int32_t sd[8];
    uint64_t q[4];
    int64_t sq[4];
    float f[8];
    double fd[4];
} BbVec;

struct BbWatch;
struct BbJitCacheEntry;

/* Exact upstream full BbCpu FIELD sequence; compile-time offsets checked
 * on native Windows AMD64 and Linux x86-64, not only the r/rip/flags prefix. */
struct BbCpu {
    uint64_t r[16];
    uint64_t rip;
    uint64_t flags;
    BbVec v[16];
    uint32_t mxcsr;
    uint64_t fs_base, gs_base;
    uint64_t tcb;
    double st[8];
    int top;
    uint16_t fcw, fsw;
    int depth;
    uint64_t stack_top;
    uint64_t jf_flags, jf_res, jf_ab;
    uint64_t jit_link;
    struct BbJitCacheEntry *jit_cache;
    uint64_t instructions;
    struct BbWatch *watch;
    uint32_t recomp_pending;
};
#if defined(__cplusplus)
#define ABI_ASSERT static_assert
#else
#define ABI_ASSERT _Static_assert
#endif
#define CPU_OFFSET(field, expected) ABI_ASSERT(offsetof(struct BbCpu, field) == (expected), "upstream BbCpu ABI drift: " #field)
ABI_ASSERT(sizeof(BbVec) == 32, "upstream 256-bit vector state");
CPU_OFFSET(r,0);
CPU_OFFSET(rip,128);
CPU_OFFSET(flags,136);
CPU_OFFSET(v,144);
CPU_OFFSET(mxcsr,656);
CPU_OFFSET(fs_base,664);
CPU_OFFSET(gs_base,672);
CPU_OFFSET(tcb,680);
CPU_OFFSET(st,688);
CPU_OFFSET(top,752);
CPU_OFFSET(fcw,756);
CPU_OFFSET(fsw,758);
CPU_OFFSET(depth,760);
CPU_OFFSET(stack_top,768);
CPU_OFFSET(jf_flags,776);
CPU_OFFSET(jf_res,784);
CPU_OFFSET(jf_ab,792);
CPU_OFFSET(jit_link,800);
CPU_OFFSET(jit_cache,808);
CPU_OFFSET(instructions,816);
CPU_OFFSET(watch,824);
CPU_OFFSET(recomp_pending,832);
ABI_ASSERT(sizeof(struct BbCpu) == 840, "upstream complete BbCpu size");
ABI_ASSERT(offsetof(RcApi, version)==0 && offsetof(RcApi, image_base)==8 &&
           offsetof(RcApi, step)==16 && offsetof(RcApi, call)==24 &&
           offsetof(RcApi, tail)==32 && offsetof(RcApi, bail)==40 &&
           offsetof(RcApi, trace)==48 && sizeof(RcApi)==56,
           "upstream RcApi-v4 callback ABI");
ABI_ASSERT(offsetof(RcFunction,offset)==0 &&
           offsetof(RcFunction,size)==8 &&
           offsetof(RcFunction,hash)==16 &&
           offsetof(RcFunction,fn)==24 &&
           offsetof(RcFunction,direct)==32 &&
           sizeof(RcFunction)==40,"upstream function dispatch ABI");
#undef CPU_OFFSET
#undef ABI_ASSERT
#endif
