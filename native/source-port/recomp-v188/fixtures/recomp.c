/* Synthetic independent exact-style upstream emitter table, no game code. */
#include "recomp_abi.h"
extern void synthetic_generated_fn(BbCpu *cpu);
extern void v188_init_synthetic(const RcApi *api);
static RcFn direct_fn = synthetic_generated_fn;
static const RcFunction table[] = {{0x1000, 12, 0x17, synthetic_generated_fn, &direct_fn}};
/* On PE/COFF the Unix visibility attribute doesn't export. Linker /EXPORT does. */
__attribute__((visibility("default"))) const RcFunction *bb_recomp_init(const RcApi *api, size_t *count) {
    if (!api || !count || api->version != BB_RECOMP_API_VERSION || !api->step) return 0;
    v188_init_synthetic(api);
    *count = sizeof(table) / sizeof(table[0]);
    return table;
}
