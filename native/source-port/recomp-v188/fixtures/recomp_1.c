#include "recomp_abi.h"
struct BbCpu { uint64_t r[16]; uint64_t rip; };
static const RcApi *runtime_callbacks;
void v188_init_synthetic(const RcApi *api) { runtime_callbacks = api; }
void synthetic_generated_fn(BbCpu *cpu) {
    cpu->r[0] += 7;
    cpu->rip = runtime_callbacks->step(cpu);
}
