# Native V384 — V245/V226/V239 real import chain + V382/V383 native-only AOT

Date: 2026-11-12. Based on V383 draft PR #113.

## Real source-level integration
V245 already builds a real Windows native `RcApi` callback chain:
- V226 math interceptor routes 23 verified import signatures;
- V239 clock interceptor routes 2 guest-named TSC functions using Windows QPC;
- `bb_recomp_init` registers compiled AOT `RcFunction` entries and stores a live pointer to the final clock wrapper.
- Previously any unrecognized call forwarded all the way to a caller's base RcApi, which could be an interpreter/translator. This is unacceptable for the requested strict standalone native-game goal.

`native_boot_chain_v384.{h,c}` now finalizes that chain AFTER V245 successfully registered its native table but BEFORE game threads execute. It verifies the real chain identity (V381 strict abort-only base, V226 -> V239, source pointer and exact original-image base), all AOT entries, and rejects any conflict between AOT function entrypoints and math/clock import addresses. Then it:
1. Calls V381 full-supplied-registry trusted owner-code attestation, installing all direct AOT slots fail-atomically;
2. Calls V382 to build a *snapshot* of the exact compiled entrypoints using V383 pinned logical guest-stack writes;
3. Publishes once-only process-lifetime native AOT `RcApi.call` and `RcApi.tail`;
4. Updates V226's immutable pre-thread original fallback so unrecognized math/clock targets now reach native AOT or ABORT; updates the final V239 `tail` callback to native-only;
5. Retains V381 abort-on-interpreter `step` and `bail` for unknown guest-code paths and marks the chain finalized;
6. Blocks V245's older V261/V268 AOT-direct-link/revoke APIs after finalization to protect the immutable published dispatch table.

`test_native_boot_chain_v384.c` exercises the REAL V245 Windows math/clock registration chain, synthetically registered native AOT addition/multiplication via V382, and actual V383 logical guest-stack return addresses. It checks that the same generated RcApi pointer was updated, tail works, AOT/import address collisions fail, math pow and clock frequency still route as expected, finalized AOT direct slots cannot be revoked, and no original guest interpreter is ever called. The test uses only original-free invented addresses and generated-style toy functions.

## CRITICAL: mixed VM models — NOT production ready
This is *not* a unified Bloodborne guest virtual memory implementation. V226/V239 currently use raw native pointers to a separately checked host-aliased stack, while V383 accepts a LOGICAL guest address translated into a caller-owned `_Atomic(uint64_t)` array. The synthetic integration fixture deliberately exercises these two valid, separate memory backings without claiming their equivalence. Production **must** replace V224/V239 direct guest pointer dereferences with the same validated native VM read/write lease/atomic semantics used by generated game code and by the native CALL/TAIL dispatcher. Do not pass arbitrary logical V383 guest addresses to the current math/clock import handlers.

This finalize API **MUST** be called after single-threaded bootstrap and before anyone calls generated code, and all route/service/stack/owner contexts must remain alive until process exit. A failure before publication may revoke direct slots, but a successful V382 publication cannot be undone/hot reloaded. Future owner-code ABI and runtime memory validation is mandatory.

## Pinned provenance
`bloodborne-native/bloodborne-recomp` `8f31ec7c41f252730c6325d52647046baef7549f`, `src/recomp/rc.h`, `src/cpu/recomp.c`: V4 CALL pushes return, TAIL uses existing return; `step`/`bail` translator methods forbidden. Used through pinned public upstream headers and dependency-only build in Windows CI.
Microsoft Win64 x86-64 PE32+ is native Windows despite use of historical Win32 APIs. Linux ELF64 native runtime requires a separately ported clock/OS import chain; V236 explicitly returns unsupported on Linux.

## Evidence
- The new files and V245 updated struct/guards are committed on `feature/native-v384-boot-chain-compose-20261112`; draft PR will be opened against V383.
- New GitHub Actions Windows job uses publicly pinned original-free upstream headers and genuine Win64 `clang-cl` compilation. Test must pass before integration can be marked validated; queued is not green.
- Public synthetic tests are NOT Bloodborne 1.09 original AOT coverage, full independent PE32+/ELF64 game, game DLC/saves/AI/physics, renderer, original online or server/launcher. No commercial original game source, files, keys, decoded shaders or credentials are to enter public GitHub or CI.

## Next P0 / later system priorities
1. Replace direct host-aliased guest-pointer memory in 23 math and 2 clock wrappers with a common actual owner-game VM API. Support sizes 1/2/4/8, allocations, permissions, pin/unpin, source AOT memory ordering and stack fault semantics. Validate original memory behavior on owner-controlled private 1.09 data, multi-thread long-duration soak, TSAN/hardware.
2. Reconcile AOT function table with actual original 1.09 entirety, including import stubs, patched/functions/hooks, setjmp, math and clock aliases, dynamic dispatch, native game entrypoint and correct full PE/ELF executable linking.
3. Build native Vulkan/D3D12 real original GPU renderer and streaming, shader/residency/fence/device-loss and frame pacing stable with simulation correctness, real CPU/GPU benchmarks. Then full gameplay/DLC/saves/NG+/online/LAN/client/server/launcher/KBM/controllers/QoL.
4. Keep macOS ARM64 as an architectural goal with distinct AOT ARM64 original-game compile and native Metal/Vulkan portability. Keep playable BBPort and BBSC Ultimate Yharnam Together separately.
