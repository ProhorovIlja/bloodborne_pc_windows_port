/* Only synthetic generated-function ABI fixture. NOT copyrighted Bloodborne code. */
#include "recomp_abi.h"
#include <stddef.h>
struct BbCpu { uint64_t r[16]; uint64_t rip; };
static const RcApi *host_api;
static void synthetic_function(BbCpu *cpu) {
    cpu->r[0] += 7;
    cpu->rip = host_api->step(cpu);
}
static RcFn ptr = synthetic_function;
static const RcFunction functions[] = {{0x1000, 12, 0x17, synthetic_function, &ptr}};
RC_EXPORT const RcFunction *bb_recomp_init(const RcApi *api, size_t *count) {
    if (!api || !count || api->version != BB_RECOMP_API_VERSION || !api->step)
        return NULL;
    host_api = api;
    *count = sizeof(functions) / sizeof(functions[0]);
    return functions;
}
