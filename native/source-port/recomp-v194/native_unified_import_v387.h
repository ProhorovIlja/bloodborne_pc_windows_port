/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V387: the ORIGINAL V245 / V384 Windows-native RcApi chain,
 * now using one permissioned V386 multi-region guest memory for both
 * compiled AOT CALL/TAIL and all supported math / clock import writes.
 */
#ifndef SHYT_NATIVE_UNIFIED_IMPORT_V387_H
#define SHYT_NATIVE_UNIFIED_IMPORT_V387_H
#include "native_boot_chain_v384.h"
#include "native_multi_region_vm_v386.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytUnifiedImportV387 {
    ShytAotServicesV245 *services;
    ShytNativeBootChainV384 *chain;
    ShytNativeVmV386 *vm;
    void (*native_fallback)(BbCpu *,uint64_t,uint64_t);
    uint64_t math_targets[23];
    uint8_t math_opcodes[23];
    uint64_t clock_ticks, clock_frequency;
    uint8_t ready,published;
} ShytUnifiedImportV387;
/* The V383 sidecar is required only by V384's original single-threaded
 * structural preflight. It MUST name an exact already registered R+W
 * V386 region (same base, count and atomic backing). Once finalized,
 * V382's native CALL/TAIL stack_write is V386, NOT the V383 sidecar.
 * No original-game code or retail PS4 ELF/SELF is loaded here.
 */
int shyt_native_boot_finalize_multiregion_v387(
    ShytNativeBootChainV384 *chain,
    ShytAotServicesV245 *services,
    const RcApi *strict_base,
    ShytNativeStackV383 *legacy_preflight_stack,
    ShytNativeVmV386 *vm,
    ShytStrictAotAttestV381 attester, void *attest_ctx);

/* Prepare final Win64 math+clock importer AFTER native-only V387 AOT
 * bootstrap, single-threaded and before any generated game worker.
 * The 23 names and positions must match the existing V245 import
 * table. Returns 0 without mutation on invalid descriptors or VM.
 */
int shyt_unified_import_prepare_v387(
    ShytUnifiedImportV387 *route, ShytAotServicesV245 *services,
    ShytNativeBootChainV384 *chain, ShytNativeVmV386 *vm,
    const ShytMathImportDesc *known_math_imports, size_t count);

/* +1 handled; 0 unknown (native-only fallback required); -1 known
 * but forbidden/invalid guest region/permissions. On -1 CPU and
 * mapped guest memory remain unchanged. A valid frexp exponent output
 * can be in a DIFFERENT R/W V386 region from the guest return stack.
 */
int shyt_unified_import_try_v387(
    ShytUnifiedImportV387 *route, BbCpu *cpu,
    uint64_t target, uint64_t next);

/* One process-lifetime irreversible RcApi.call publisher. Unknown
 * targets reach ONLY V382 verified native AOT. Unsafe known target
 * ABORTS, NEVER falls back to V226/V239 raw host pointer adapters.
 * step/bail remain V381 abort-only. No hot unload or reactivation.
 */
int shyt_unified_import_publish_v387(ShytUnifiedImportV387 *route);
#ifdef __cplusplus
}
#endif
#endif
