# V261: real native bootstrap -> attested RcFunction.direct AOT fastpath

2026-11-01. True no-EBOOT Windows port, Draft PR #84.
Original public upstream `bloodborne-native/bloodborne-recomp`
`8f31ec7c41f252730c6325d52647046baef7549f`.

## Actual new integration

Previously V259's direct slot linkage had only a standalone test
and V245's actual native `bb_recomp_init` bootstrap returned its
`RcFunction` table without a way to configure the generated module's
`RcFn* direct` slots. V261 now exposes the owner-only, opt-in
`shyt_aot_services_link_direct_v261()` after successful V245 startup.

It uses the actual original `RcFunction` registration table with
a live `RcApi`, checks its layout with V257 and invokes V259's
per-function code attester. It clears unapproved/stale direct slots;
only approved, non-excluded game functions can use the native
C-to-C direct function pointer. All other calls remain on the
original `RcApi.call` fallback path. No runtime PS4 ELF is needed
to set these pointers. Invoke *before* launching game worker threads.

The V245 Win64 executable fixture now registers a generated-style C
function with `direct=&native_direct_slot`, runs it through V226 math
and V239 QPC TSC handlers, first denies direct slots, enables only a
synthetic exact-hash match, executes the actual direct function pointer
through original `BbCpu`, and revokes it. It verifies all memory-pin
callbacks and the standard import fallbacks. Its synthetic fake hash
is for CI ONLY: a production game build must NEVER use this attester.

## Remaining validation/roadblocks

The original `src/cpu/recomp.c` verifies per-function hashes from the
original game image and skips code modified by patches/hooking. The
private genuine Windows port must provide owner-produced exact game
function attestation that handles live patches and code replacement,
and must ensure fallback functions do not accidentally invoke an
absent PS4 translator. This must match the real private 1.09 image
and every recompiled module. Current 54/384 partial Windows COFF
progress is not a completed executable.

The native startup and original AOT code need the rest of the Windows
subsystems (graphics, resources, streaming, audio, input, online)
before Bloodborne can actually reach the game/menu. Native
`RcFunction.direct` linking is one bounded step in that process.

GitHub Actions latest result not verified. No private retail code
published. No Fornex deployment.
