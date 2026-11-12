/* SPDX-License-Identifier: GPL-2.0-or-later
 * V384 native-only RcApi composition on top of real V245 math+clock chain.
 * Public synthetic host engineering only; not an original-game port.
 */
#ifndef SHYT_NATIVE_BOOT_CHAIN_V384_H
#define SHYT_NATIVE_BOOT_CHAIN_V384_H
#include "native_aot_services_bootstrap_v245.h"
#include "native_aot_route_v382.h"
#include "native_pinned_stack_v383.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShytNativeBootChainV384 {
    ShytNativeAotRouteV382 route;
    ShytStrictAotProofV381 proof;
    uint8_t published;
} ShytNativeBootChainV384;

/* Verify that V245 was really bootstrapped FROM a V381 trap-only base,
 * V226 math -> V239 clock -> registered AOT table, with no conflicting
 * compiled function and import targets. Inspect only; no mutation. */
int shyt_native_boot_preflight_v384(
    const ShytAotServicesV245 *services,
    const RcApi *strict_base, const ShytNativeStackV383 *stack);

/* ONLY call single-threaded, after V245 bootstrap / real_recompiled_init,
 * before ANY generated code or worker executes. All owner attestation
 * must independently verify original 1.09 bytes, patches and coverage.
 *
 * 1. Validate complete supplied function table (NOT whole-game coverage).
 * 2. V381 attests every function + activates its direct slots atomically.
 * 3. V382 snapshots AOT entries, wires V383 safe logical-stack writer.
 * 4. Publish V382 native-only CALL/TAIL once and patch V245 math
 *    fallback + V239 final TAIL. Unknown calls go to an ABORT trap,
 *    never to interpreter/PS4 guest code. step/bail still ABORT.
 *
 * V224 math and V239 clock import handlers still require a separate,
 * stable, valid HOST-ALIAS guest memory mapping and raw pointer writes.
 * V383 logical mapping is NOT an equivalent backing for those imports.
 * This is therefore not production-ready unified game VM integration.
 */
int shyt_native_boot_finalize_v384(
    ShytNativeBootChainV384 *chain,
    ShytAotServicesV245 *services,
    const RcApi *strict_base,
    ShytNativeStackV383 *stack,
    ShytStrictAotAttestV381 attester, void *attest_ctx);

/* Once published, chain, services, stack and all callbacks must remain
 * alive and immutable until process exit. No hot reload or unpublish.
 * V245 legacy V261/V268 direct-slot mutation is blocked after commit. */
#ifdef __cplusplus
}
#endif
#endif
