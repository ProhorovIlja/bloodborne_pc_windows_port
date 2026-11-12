/* SPDX-License-Identifier: GPL-2.0-or-later
 * V385 replaces final math/clock guest pointer writes with one logical
 * VM shared by V384's published AOT CALL/TAIL dispatch. Native Win64 only
 * until clock and generated original-game ABI are ported to other hosts.
 */
#ifndef SHYT_NATIVE_UNIFIED_IMPORT_V385_H
#define SHYT_NATIVE_UNIFIED_IMPORT_V385_H
#include "native_boot_chain_v384.h"
#include "native_guest_vm_v385.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytUnifiedImportV385 {
    ShytAotServicesV245 *services;
    ShytNativeBootChainV384 *chain;
    ShytGuestVmV385 *vm;
    void (*native_fallback)(BbCpu *,uint64_t,uint64_t);
    uint64_t math_targets[23];
    uint8_t math_opcodes[23];
    uint64_t clock_ticks, clock_frequency;
    uint8_t ready, published;
} ShytUnifiedImportV385;
/* PRE-CONDITION: V384 has finalized its original native V245 chain with
 * the SAME ShytNativeStackV383 backing that this VM wraps.
 * 23 import descriptors MUST match exact V245 math table entries.
 * Require owner-known build-time import offsets; no runtime PS4 ELF.
 * Does not modify global callback routing on any failure.
 */
int shyt_unified_import_prepare_v385(
    ShytUnifiedImportV385 *route,
    ShytAotServicesV245 *services,
    ShytNativeBootChainV384 *chain,
    ShytGuestVmV385 *vm,
    const ShytMathImportDesc *math_names, size_t count);
/* Publish exactly once, single-threaded BEFORE generated code runs.
 * Known math/clock calls use only VM logical guest addresses;
 * unknown targets go straight to V384's already validated native-only
 * AOT callback (which aborts on unresolved target).
 * V245's OLD raw-pointer handlers must never be separately invoked
 * in production after this finalization.
 */
/* Explicit diagnostic before publication: +1 handled by native VM,
 * 0 unknown target, -1 known import but unsafe. Unknown may be sent
 * to native-only V382; -1 must abort/trap without guest code fallback.
 * On -1 guest CPU registers/memory remain unchanged.
 */
int shyt_unified_import_try_v385(ShytUnifiedImportV385 *route,
    BbCpu *cpu, uint64_t target, uint64_t next);
int shyt_unified_import_publish_v385(ShytUnifiedImportV385 *route);
#ifdef __cplusplus
}
#endif
#endif
