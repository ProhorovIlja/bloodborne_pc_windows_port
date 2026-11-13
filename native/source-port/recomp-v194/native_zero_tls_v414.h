/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_ZERO_TLS_V414_H
#define SHYT_ZERO_TLS_V414_H
#include "full_cpu_abi_v194.h"
#include "native_generated_memory_v390.h"
/* A single zero-initialized static TLS block immediately below the
 * logical TCB. Caller owns this dedicated span and the CPU. Not a
 * dynamic TLS allocator, module linker or complete PS4 TCB layout. */
static inline int shyt_zero_tls_v414(ShytNativeOsVmV388 *owner,BbCpu *cpu,
    uint64_t tcb,size_t bytes,size_t alignment) {
    if(!owner || !cpu || shyt_generated_owner_v392()!=owner ||
       cpu->tcb || cpu->fs_base || bytes==0 || bytes>65536u || (bytes&7u) ||
       alignment<8u || alignment>4096u || (alignment&(alignment-1u)) ||
       tcb<(uint64_t)bytes || (tcb&(alignment-1u)) ||
       ((tcb-(uint64_t)bytes)&(alignment-1u)) ||
       !shyt_generated_zero_v412(tcb-(uint64_t)bytes,bytes))return 0;
    cpu->tcb=tcb;
    cpu->fs_base=tcb;
    return 1;
}
#endif
