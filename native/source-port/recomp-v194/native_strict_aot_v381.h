/* SPDX-License-Identifier: GPL-2.0-or-later
 * V381: strict native AOT diagnostic. Never delegate guest-code fallbacks.
 * No game code/assets or original PS4 loader in this public source.
 */
#ifndef SHYT_NATIVE_STRICT_AOT_V381_H
#define SHYT_NATIVE_STRICT_AOT_V381_H
#include "../recomp-v187/recomp_abi.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef int (*ShytStrictAotAttestV381)(
    void *context, uint64_t original_address,
    uint64_t code_bytes, uint64_t original_code_hash);

typedef struct ShytStrictAotProofV381 {
    size_t functions_attested;
    uint8_t no_guest_fallback_callbacks;
    uint8_t owner_game_startup_proven; /* NEVER set by this contract */
} ShytStrictAotProofV381;

/* Initialize a native RcApi v4 base with non-returning fail-closed
 * callbacks. This base can be wrapped by audited native import handlers
 * BEFORE starting gameplay threads. In particular RcApi.call and .tail
 * may be needed for legitimate native indirect control flow: until an
 * independent AOT-only resolver replaces these traps, they will abort.
 *
 * No callback from this API ever invokes an interpreter, JIT, translator,
 * original EBOOT, PS4 ELF, or untrusted guest memory.
 */
int shyt_strict_aot_base_v381(RcApi *out, uint64_t image_base);

/* Diagnostic: confirms that this exact base still contains ONLY V381
 * fail-closed callbacks. Wrappers installed above it are not inspected. */
int shyt_strict_aot_is_base_v381(const RcApi *api);

/* Before game threads, atomically accept/reject a fully trusted owner-
 * attested direct-call registry. Every generated function MUST have a
 * unique writable direct slot initially NULL. A complete preflight and
 * explicit per-function code hash attestation precede ANY activation.
 *
 * The attester must independently check the owner's original code
 * bytes and patch status. A mock always-true callback is unsafe for
 * original game code and is used ONLY in synthetic public tests.
 * Do not use after threads start or with memory that can be modified.
 *
 * Passing this test only means a small, supplied table can dispatch
 * natively using a fail-closed base API; NEVER proof that all original\n * game functions are present.
 */
int shyt_strict_aot_activate_v381(
    const RcApi *strict_base,
    const RcFunction *functions, size_t count, uint64_t image_base,
    ShytStrictAotAttestV381 attester, void *ctx,
    ShytStrictAotProofV381 *out);
#ifdef __cplusplus
}
#endif
#endif
