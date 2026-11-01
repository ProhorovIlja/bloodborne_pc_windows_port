/* SPDX-License-Identifier: GPL-2.0-or-later
 * V223: explicit PS4 SysV guest CPU -> native Win64 host math bridge.
 * No EBOOT runtime or third-party HLE. Caller validates guest RSP and
 * pointers; no FENV/errno/exception-flag fidelity is asserted.
 */
#include "native_math_guest_bridge_v223.h"
#include "native_math_shim_v222.h"
#include <string.h>

static void guest_ret(BbCpu *cpu) {
    uint64_t ret;
    memcpy(&ret, (const void *)(uintptr_t)cpu->r[RSP], sizeof(ret));
    cpu->r[RSP] += sizeof(ret);
    cpu->rip = ret;
}
#define DD1(name) static void wrap_##name(BbCpu *cpu) { \
    const double a = cpu->v[0].fd[0]; \
    cpu->v[0].fd[0] = shyt_math_##name(a); guest_ret(cpu); }
#define DD2(name) static void wrap_##name(BbCpu *cpu) { \
    const double a = cpu->v[0].fd[0], b = cpu->v[1].fd[0]; \
    cpu->v[0].fd[0] = shyt_math_##name(a,b); guest_ret(cpu); }
#define FF1(name) static void wrap_##name(BbCpu *cpu) { \
    const float a = cpu->v[0].f[0]; \
    cpu->v[0].f[0] = shyt_math_##name(a); guest_ret(cpu); }
#define FF2(name) static void wrap_##name(BbCpu *cpu) { \
    const float a = cpu->v[0].f[0], b = cpu->v[1].f[0]; \
    cpu->v[0].f[0] = shyt_math_##name(a,b); guest_ret(cpu); }
#define DIP(name) static void wrap_##name(BbCpu *cpu) { \
    const double a = cpu->v[0].fd[0]; int * const p = (int *)(uintptr_t)cpu->r[RDI]; \
    cpu->v[0].fd[0] = shyt_math_##name(a,p); guest_ret(cpu); }
#define FIP(name) static void wrap_##name(BbCpu *cpu) { \
    const float a = cpu->v[0].f[0]; int * const p = (int *)(uintptr_t)cpu->r[RDI]; \
    cpu->v[0].f[0] = shyt_math_##name(a,p); guest_ret(cpu); }
#define DII(name) static void wrap_##name(BbCpu *cpu) { \
    const double a = cpu->v[0].fd[0]; const int n = (int)cpu->r[RDI]; \
    cpu->v[0].fd[0] = shyt_math_##name(a,n); guest_ret(cpu); }
#define FII(name) static void wrap_##name(BbCpu *cpu) { \
    const float a = cpu->v[0].f[0]; const int n = (int)cpu->r[RDI]; \
    cpu->v[0].f[0] = shyt_math_##name(a,n); guest_ret(cpu); }

DD2(atan2) DD2(fmod) DD2(pow)
DD1(acos) DD1(tan) DD1(asin) DD1(atan) DD1(exp) DD1(exp2)
DIP(frexp) DII(ldexp)
FF2(fmodf) FF2(atan2f) FF2(powf)
FF1(tanf) FF1(acosf) FF1(asinf) FF1(atanf) FF1(expf) FF1(tanhf) FF1(exp2f)
FIP(frexpf) FII(ldexpf)

typedef struct { const char *name; ShytGuestMathFn fn; } Entry;
static const Entry kEntries[] = {
    {"acos",wrap_acos}, {"acosf",wrap_acosf}, {"asin",wrap_asin},
    {"asinf",wrap_asinf}, {"atan",wrap_atan}, {"atan2",wrap_atan2},
    {"atan2f",wrap_atan2f}, {"atanf",wrap_atanf}, {"exp",wrap_exp},
    {"exp2",wrap_exp2}, {"exp2f",wrap_exp2f}, {"expf",wrap_expf},
    {"fmod",wrap_fmod}, {"fmodf",wrap_fmodf}, {"frexp",wrap_frexp},
    {"frexpf",wrap_frexpf}, {"ldexp",wrap_ldexp}, {"ldexpf",wrap_ldexpf},
    {"pow",wrap_pow}, {"powf",wrap_powf}, {"tan",wrap_tan},
    {"tanf",wrap_tanf}, {"tanhf",wrap_tanhf}
};
ShytGuestMathFn shyt_guest_math_v223_find(const char *name) {
    if (!name) return NULL;
    for (size_t i=0; i < sizeof(kEntries)/sizeof(kEntries[0]); ++i)
        if (strcmp(name,kEntries[i].name)==0) return kEntries[i].fn;
    return NULL;
}
