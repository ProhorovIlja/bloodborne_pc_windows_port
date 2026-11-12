# Native V394 — REAL pinned bbrecomp-generated RcApi.call enters trusted host callback and recovers via V393

Date: 2026-11-12. Branch `feature/native-v394-generated-host-callback-20261112` in `ProhorovIlja/bloodborne_pc_windows_port`. Base: V393 draft PR #123; prior V392 #122, V391 #121, V390 #120 and V389 #119. This is the **independent source port** research track, NOT the playable BBPort or BBSC Ultimate Yharnam Together client/server/launcher.

## Critical issue closed in synthetic-source evidence

V393's bounded `setjmp/longjmp` cooperative recovery was exercised from a **trusted preflight callback**, before executing any generated guest instructions. This did not prove a host callback genuinely invoked **from real original-upstream-generated C** could raise into the still-live recovery checkpoint without stranding the V386 memory lease.

Pinned public `bloodborne-native/bloodborne-recomp` original full-function generator `tools/recomp/bbrecomp.c`, revision `8f31ec7c41f252730c6325d52647046baef7549f`, translates invented x86-64 `CALL RAX; RET` to a real `rc->call(c,target,next)` callback inside generated C. This is the exact seam V394 tests, **without** introducing a PS4 interpreter or runtime original PS4 EBOOT.

## Actual V394 files / implementation

1. `generate_host_call_v394.py` copies the pinned original-free V391 code-generation fixture, adds a SIXTH instruction sequence at guest offset `0x10a0` with raw bytes `FF D0 C3` (= `CALL RAX; RET`). The synthetic ELF64 file is invented, remains confined to GitHub runner TEMP and is used by the genuine pinned bbrecomp compiler **only at build time**, not loaded by the resulting program. Requires source-locked public `bbrecomp.c` blob hash `f5032c9ead4988579e005af8a0a0ce4ba4ab66d8`, checks all six emitted native RcFunction bodies and slots, real LOCK CAS, SSE/AVX memory helper emission, and a generated `rc->call(c,…)` seam, rejecting step-interpreter fallback.

2. `test_native_generated_host_callback_v394.c` executes **actual emitted C** for the six synthetic x86-64 function bodies, compiled and linked as native host code. First five inherited LOCK CMPXCHG, SSE128 MOVDQU, AVX256 VMOVDQU, guest memory bounds, cross-word LOCK fail-closed, V389 remap and V392/393 scoped nested/pinned VM tests. The newly generated `f_10a0` has a registered trusted `RcApi.call` handler, not a hand-written native function stand-in. It validates:
   - Normal generated `CALL RAX` enters the host `RcApi.call` callback; callback returns to genuine generated `RET` with correct guest CPU RSP/RIP, RAX and no remaining V390 lease.
   - Explicit trusted host callback calls `shyt_generated_raise_v393(91)` **while executing actual generated RcFn**, which jumps to the entry wrapper's live C11 checkpoint and releases the owned C11 V390/V386 OS-backed VM lease. The generated RET is skipped, no interpreter fallback; V389 PAUSE can succeed immediately afterward.
   - Nested `CALL RAX`: a host callback itself invokes the **same** real generated function through an inner V393 recoverable scope. The inner callback raises code 97; the inner borrowed scope unwinds without releasing the outer lease; outer call subsequently returns normally and releases its lease. While the outer lease is active, V389 PAUSE is refused. After the outer return, PAUSE succeeds. This path validates callback nesting on one guest VM without a guest interpreter.
   - All inherited V393 trusted **preflight** recovery/negative paths remain tested, but the NEW proof is specifically a callback reached from real generated code.

3. `verify_generated_host_callback_v394.py` extends V393 Linux ELF-object symbol and relocation provenance to exactly six generated RcFn definitions, including `f_10a0`, and V390 guest-memory bridge symbols with actual ELF relocations. It also verifies the **exact V390 overlay** against real generated function-shard C and checks the real `f_10a0` body emits `rc->call` rather than interpreter `rc->step`. `test_verify_generated_host_callback_v394.py` exercises deliberately malformed source/ELF symbol and bridge dependency negatives. A registered function-pointer callback does not necessarily appear as an undefined object symbol: the object audit is **not** a proof that every direct guest pointer or imported code path was eliminated.

4. `.github/workflows/native-v394-real-generated-host-callback.yml` builds the same pinned public offline full-function recompiler, emits 6 invented x86 function bodies and instruments every generated shard with V390, asserts V392 complete synthetic code-generation coverage, V394 exact compiled ELF symbol/relocation audit and source `rc->call`, then compiles/runs actual real source generated C plus V393 host checkpoint on Linux (GCC/Clang and ASan/UBSan), Windows x64 (clang-cl strict `/W4 /WX` on native host, actual PE32+ compiled and executed) and macOS ARM64 host-only C (when runner available). Never packages original commercial game files, owner code, keys or credentials.

## Verified CI state at initial documentation

The first V394 branch push Linux job #131328233022 (run #43259952773) completed SUCCESS, with markers:
`NATIVE_V394_PINNED_GENERATED_RcApi_CALL_HOST_CALLBACK_PASS`,
`NATIVE_V392_ALL_REAL_GENERATED_AOT_SHARDS_INSTRUMENTED_PASS`,
`NATIVE_V394_GENERATED_CALL_OBJECT_NEGATIVE_TESTS_PASS`,
`NATIVE_V394_REAL_GENERATED_CALL_RAX_ELF_OBJECT_ROUTING_PASS`,
`NATIVE_V394_REAL_GENERATED_RcApi_CALL_RECOVERY_AND_NESTED_PASS` emitted **three times** for Clang, GCC and ASan/UBSan. Windows and macOS jobs queued at that check. **Confirm final PR head CI status before claiming success there.**

Prior V393 Linux and Windows CI completed success on current previous commit; macOS jobs were **CANCELLED**, not test failures, likely due unavailable runner resources. Do not represent cancelled macOS as passing or as a demonstrated Apple Silicon game.

## Strict production safety limits

Only an **explicit trusted, synchronous, same-thread host callback** that raises through a live V393 scope is supported. This is NOT a general-purpose safe exception mechanism for arbitrary raw C `longjmp`, `SIGSEGV`, access violation, POSIX signal handlers, Windows SEH, C++ unwinding, thread cancellation or `abort`; those can skip pinned lease destructors and remain production blockers. All skipped C frames must own no unmanaged locks/resources requiring cleanup. The host must implement explicit error/result and unwind semantics per import; old raw-pointer V226/V239 compatibility adapters remain outside proof. The original game imports, thread scheduling, exceptions, original AOT functions, direct call graph, game startup, page aliases and genuine native renderer are not included in these tests.

The user seeks a **fully independent original Bloodborne 1.09 Windows x64 PE32+/Linux ELF64 native game without PS4 runtime or original PS4 EBOOT** (and eventually Mac ARM64 Mach-O), accurate AI/physics/campaign+DLC/chalices/saves, rendering/Vulkan/D3D12/streaming/shaders, high performance/frame pacing, PC keyboard/mouse chords/controllers/NG+, robust LAN/P2P/server-client online and launcher options/quality/stability, optional supported HDR/upscalers/Reflex. None of the real game playable, renderer/network, native executable linker/import completeness or measured performance milestones are established by these six synthetic functions. Retail game and DS3 assets/source private; never push commercial bytes to public GitHub or CI.

## Next P0

1. Verify final V394 PR Linux/Windows/macOS results; repair actual failures, not reduce checks.
2. Expand **owner-private original 1.09** source AOT function and import closure, identify genuine all callbacks and safe host unwind strategy, prove every generated guest memory op is VM-mediated at source AND binary level; ensure no guest translator/interpreter fallback path is reachable. Real Linux-native clock/service imports.
3. Make a genuine standalone independent original Bloodborne executable game startup on Windows/Linux with owner-only licensed data, full assets/geometry/shaders native renderer and correct game simulation before prioritizing user-facing upscaler, graphics, PC controls, NG+/QoL and online/client/server/launcher optimization. Keep compatibility-based playable BBPort / BBSC Yharnam Together Ultimate separate.
4. Keep source/provenance metadata for external GitHub repos/forks/PR/branches and connected Drive files, review licenses, do not claim exhaustive global search.

**V394 is demonstrated infrastructure only, not a playable original-game native port.**
