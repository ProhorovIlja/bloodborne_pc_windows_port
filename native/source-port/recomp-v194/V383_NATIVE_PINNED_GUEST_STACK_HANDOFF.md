# V383 — bounded atomic guest-stack lease wired into native-only AOT CALL/TAIL

Date: 2026-11-12. Based on draft V382 PR #112. All new work is public original-free source, synthetic tests and CI only. This is not a working original game or a claim of full no-guest runtime closure.

## Specific integration, not a placeholder

`native_pinned_stack_v383.{h,c}` implements an actual bounded contiguous logical-guest-to-host 64-bit memory mapping for STACK words. An initialized C11 `_Atomic(uint64_t)` array is externally owned, with up to 1,048,576 words. Guest addresses are translated to indexes; they are NEVER automatically dereferenced as host pointers. The mapping is immutable while live. The caller MUST supply real, permanently valid backing storage and map it according to the future native game's host virtual memory manager.

`shyt_native_stack_write_v383(ctx,guest_address,value)` is a direct V382 `ShytNativeAotStackWriteV382` callback: it refuses unaligned, out-of-range, closed or malformed addresses without changing memory; otherwise atomically writes the validated word using C11 release ordering. The matching `read` uses acquire ordering for native synthetic return semantics.

The state has an atomic lease count plus permanent CLOSED bit. Successful pins are required while using backing; close immediately refuses new pins but cannot unmap until every existing lease is released. `quiescent` signals all leases drained. Free/unmap/reusing the mapping is the OWNER's responsibility, only after quiescence AND all threads that may invoke callbacks have fully exited. No unverified `VirtualQuery`, `mmap`, `VirtualAlloc`, PS4 guest executable loaders or page permissions are hidden in this component. Existing `RcApi.call` still intentionally aborts on a rejected stack write instead of reaching PS4 guest translator.

`test_native_pinned_stack_v383.c` runs native recompiled-style toy `RcFn` functions with real `BbCpu` v194 pinned host ABI and V381 admission into V382 binary-search dispatch. It checks CALL pushes a return address through the mapped atomic stack, TAIL reuses an existing guest return, invalid RSP / mapped bounds / null / overflow reject without CPU mutation, close stops new pins, drained outstanding leases and no reuse or underflow. No original game code is included.

Cross-platform CI: Win64 clang-cl, Linux GCC/Clang and ASan/UBSan, macOS ARM64 host-only. Passing this CI is not equivalent to original game memory parity. Windows x64/Linux AMD64 remain primary port targets. Apple ARM64 source compilation is only a portability foundation.

## Pinned upstream reference

`bloodborne-native/bloodborne-recomp` commit `8f31ec7c41f252730c6325d52647046baef7549f`, `src/cpu/cpu_internal.h` defines `bb_store` and `bb_load`: ARM64 aligned stores use release atomic and aligned loads acquire atomic; x86 code has architecture-specific memory ordering. `src/recomp/rc.h` and `src/cpu/recomp.c` specify CALL pushes guest return and TAIL does not. This component intentionally uses C11 atomic release/acquire memory for one bounded mapping. **It does not prove equivalence for mixed raw guest-code accesses, all other guest memory widths, game synchronization primitives or actual private 1.09 object layouts.** Future VM integration must ensure all accesses use a compatible memory model.

Source:
https://github.com/bloodborne-native/bloodborne-recomp/blob/8f31ec7c41f252730c6325d52647046baef7549f/src/cpu/cpu_internal.h
https://github.com/bloodborne-native/bloodborne-recomp/blob/8f31ec7c41f252730c6325d52647046baef7549f/src/cpu/recomp.c

## Remaining blockers

1. Integrate a real native game VM: retain backed allocations, guard permissions, page protection and unmap races, dynamic stack growth, all sizes and alignments, concurrency and plain/atomic generated AOT access semantics. Reject with no mutation, no stale or dangling mappings. Expose a matching memory lease through actual original-game host imports.
2. Connect V382 process-wide `RcApi` dispatch to V245 native math/clock bootstrap in the correct order, with native-only import routing and strictly checked identity. Keep `RcApi.step` and `RcApi.bail` unavailable; no compatibility fallback.
3. Owner-only Bloodborne 1.09 full AOT function registration, original game code hashes and patch handling, indirect call graph/host import completeness, genuine standalone PE32+/ELF64 link and full game entrypoint startup. Existing V309 `/DLL /NOENTRY` lld-link probe does **not** equal a game executable.
4. Native GPU/audio/input/online/gameplay/AI/saves/physics/streaming integration and full private campaign/DLC/chalice testing. Optional DLSS/FSR/XeSS/Reflex/HDR/FG etc only when driver/hardware + SDK support is independently verified.
5. Repeat verified upstream GitHub repository/fork/branch/PR + user Drive research; never claim the entire internet/GitHub has been exhausted.

Use draft PR #113 as next handoff anchor; preserve separate playable BBPort/Yharnam Together Ultimate track, no retail assets in GitHub or public CI.
