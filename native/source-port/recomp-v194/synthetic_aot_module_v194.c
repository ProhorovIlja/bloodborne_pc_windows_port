/* V194 synthetic generated C unit, mimics upstream RcFn/RcFunction ABI.
 * This is NOT retail Bloodborne game code and proves only the executable
 * link/dispatch/guest RET boundary with an exact complete BbCpu layout.
 */
#include "full_cpu_abi_v194.h"
#include <string.h>
static void func_0(BbCpu *cpu) {
    cpu->r[0] += UINT64_C(1);
    uint64_t ret;
    memcpy(&ret, (const void *)(uintptr_t)cpu->r[4], sizeof ret);
    cpu->r[4] += 8;
    cpu->rip = ret;
}
static void func_1(BbCpu *cpu) {
    cpu->r[0] *= UINT64_C(2);
    uint64_t ret;
    memcpy(&ret, (const void *)(uintptr_t)cpu->r[4], sizeof ret);
    cpu->r[4] += 8;
    cpu->rip = ret;
}
static RcFn direct_0=func_0;
static RcFn direct_1=func_1;
static const RcFunction table[]={
    {UINT64_C(0x100),UINT64_C(16),UINT64_C(0x90705547f2bf684f),func_0,&direct_0},
    {UINT64_C(0x110),UINT64_C(16),UINT64_C(0x5a5a5a5a5a5a5a5a),func_1,&direct_1},
};
const RcFunction *bb_recomp_init(const RcApi *api, size_t *count) {
    if (!api || api->version != BB_RECOMP_API_VERSION || !count) return NULL;
    *count=sizeof(table)/sizeof(table[0]);
    return table;
}
