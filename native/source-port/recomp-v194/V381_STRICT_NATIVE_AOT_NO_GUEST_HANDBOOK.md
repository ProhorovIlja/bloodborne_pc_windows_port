# V381: strict original-game AOT admission and no-guest callback tripwire

Date: 2026-11-12. Based on V380, draft PR #110; this PR stays draft.
The source is native C11 only. NO original Bloodborne retail game code is in public GitHub or CI.

## Important upstream finding
bloodborne-native/bloodborne-recomp reports (2026-11-02) 181,521 / 181,570 functions running recompiled, 96.2% instructions covered. It still falls back to translator on remaining import stubs, setjmp, and patched/switched functions. Recompiled code is not equivalent to a fully native independent game startup; the separate bloodborne-runtime still implements PS4-specific dependencies.
https://github.com/bloodborne-native/bloodborne-recomp/blob/main/docs/RECOMPILATION.md
https://github.com/bloodborne-native/bloodborne-runtime
Original pinned table API used here: native/source-port/recomp-v187/recomp_abi.h and full_cpu_abi_v194.h.

## Committed implementation
- `native_strict_aot_v381.{h,c}` creates an `RcApi` V4 base that has no guest interpreter/translator fallback. The `step`, `call`, `tail`, and `bail` callbacks abort rather than executing compatibility code. This is a **diagnostic**, because legitimate indirect native AOT calls must eventually be served by a separate native resolver, not by these abort callbacks.
- `shyt_strict_aot_activate_v381` requires this exact strict base and the owner's verified code-hash attester, a wholly present, strictly ordered `RcFunction` registry, nonzero function sizes, no address overflow, unique aligned direct slots, and no stale direct pointer. All supplied functions are attested BEFORE any slot is published; a failed proof leaves all direct slots unchanged. Activation is single-threaded at boot. It does **not** prove the submitted table covers every function of the original game.
- The synthetic-only test compiles against the pinned original `BbCpu` ABI, checks fail atomicity, duplicate slots and offsets, stale direct pointer refusal and executing native synthetic functions without guest. On Linux/macOS it also forks and requires SIGABRT when the forbidden fallback is invoked. Windows compiles and tests the native table and guard identity; no Windows abort child is included.
- CI: Windows AMD64 clang-cl, Linux gcc/clang + sanitizers, macOS ARM64 host-only. No user retail assets, compiler-generated game code, SDK redistributions or game credentials are uploaded.

## No false game-ready claims
V381 test success does **not** demonstrate a runnable original Bloodborne, actual 1.09 private AOT completeness, executable PE32+/ELF64 game linkage, native import closure, no runtime PS4 service APIs, renderer completeness, DLC progress, playable online, or macOS ARM64 original-game recompilation. A synthetic table can pass trivially while the original game is incomplete.

## Follow-up P0 integration priorities
1. Owner-only verified original 1.09 AOT registry: strict total function coverage including import stubs, setjmp/patch-sensitive functions, all indirect control flow; isolate original code and data privately. A simple always-true attester MUST NOT qualify.
2. Replace `RcApi.call` and `RcApi.tail` tripwires with native AOT-only lookup/dispatch using verified generated function tables, correct `BbCpu` call/return/stack semantics, fail closed on unresolved targets.
3. Feed the strict base into `shyt_aot_services_bootstrap_v245` as `native_platform_api` and audit every higher-level math/clock/native OS import. An unknown target must abort rather than delegate to a guest translator. Verify no native code can bypass the strict wrappers.
4. On owner's system, run existing bounded private v204/v217/v275/v287/v309 diagnostics, then truly link 64-bit standalone game executables and perform OS process tracing to establish absence of PS4 ELF/SELF/eboot and guest code; do not write private original code into public CI.
5. Only then execute original full offline campaign, DLC, saves, physics, AI, audio and graphics with fully native host services. Keep playable BBPort and BBSC/Yharnam Together separate.

This is a strict startup safety mechanism, not a port completion milestone.
