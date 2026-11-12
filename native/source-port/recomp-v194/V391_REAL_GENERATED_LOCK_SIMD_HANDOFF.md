# Native V391 — genuine upstream whole-function LOCK CMPXCHG and SIMD128/256 against V390 VM

2026-11-12. Base Native V390 draft PR #120, with V389 dynamic quiescent page remap, V388 OS pages, V386 logical C11 atomic VM, pinned original `bloodborne-native/bloodborne-recomp` source commit `8f31ec7c41f252730c6325d52647046baef7549f`.

## Why this is meaningful
V390 first ran SIX real functions emitted by the genuine pinned upstream bbrecomp whole-function compiler against the V389 guest memory lease adapter. But V390's actual generated C fixture contained scalar/stack `rc_ld/st/lds/sts` only; CAS and vector helpers were **called by handwritten host test**, not by a real generated function. V391 addresses this specific evidence gap by creating **FIVE original-free invented x86-64 source functions**:
- `lock cmpxchg qword ptr [rdi], rsi; ret` — emits a real `rc_cas` from pinned upstream, and the V390 macro routes it through atomic C11 seq_cst guest-memory CAS.
- `movdqu xmm0, [rdi]; ret` and `movdqu [rdi], xmm0; ret` — emits real 16-byte vector memory load and store through `rc_vld/vst` mapped to V390.
- `vmovdqu ymm0, [rdi]; ret` and `vmovdqu [rdi], ymm0; ret` — emits real 32-byte vector load and store; check that all YMM bytes including high 128-bit half survive.
The actual invented x86-64 instruction bytes are source-controlled in `generate_lock_simd_v391.py`, not from Bloodborne or Dark Souls 3, and the synthetic ELF exists only during CI generation, not at program runtime.

## Actual files committed
`native/source-port/recomp-v194/generate_lock_simd_v391.py`:
- Requires pinned full upstream `bbrecomp.c` git blob `f5032c9ead4988579e005af8a0a0ce4ba4ab66d8` and pinned revision, real built generator, fresh output in non-Git runner-temp folder. Generates one synthetic ELF64 with five functions at guest offsets 0x1000, 0x1020, 0x1040, 0x1060, 0x1080.
- Audits the real generated `bb_recomp_init` table and function shard for all five RcFns and positive `rc_cas`, `rc_vld` and `rc_vst` emission. Rejects compiler/interpreter step fallback, source drift, missing functions or bloated output. Only prints bounded synthetic totals; no private source.
`native/source-port/recomp-v194/test_native_generated_lock_simd_v391.c`:
- Compiles and invokes real generated five RcFns, with original pinned RcApi v4 (`step/call/tail/bail` abort), active V390 per-thread V386 lease, and V388 OS mmap/VirtualAlloc pages plus V389 dynamic remap.
- Tests successful LOCK CMPXCHG (RAX expected preserved, guest memory updated, ZF flag), failing compare (actual observed memory in RAX, guest memory unchanged, ZF cleared), and success again after V389 remap without stale host pointer.
- Tests both 128-bit SSE and 256-bit AVX vector register loads and stores against actual OS-backed guest data, including YMM upper 128 bits and exact byte comparisons. Guest data region is bounded, R-only guest region denies write, and active generated lease blocks PAUSE/remap.
- POSIX child tests call genuine original upstream-generated CAS across two V390 backing 64-bit atomic words, CAS at read-only page, vector store at R-only page, and vector load beyond region. Each must terminate with SIGABRT, **never silently interpret, corrupt memory, or simulate an incorrectly atomic multiword LOCK**. Windows positive tests also verify mapping and denied try-store. This is test-only abort and can produce core without `ulimit -c 0`; CI sets core limit zero.
`.github/workflows/native-v391-generated-lock-simd.yml`:
- Linux builds original pinned upstream whole-function compiler from public code, using existing checked V196/V199 build-host patches. Generates synthetic ELF and real C shard, instruments AFTER original `recomp/rc.h` using V390 source-locked instrumentation, compiles and executes on Linux GCC/Clang and Linux ASan/UBSan.
- Uploads only original-free invented generator C shard and pinned PUBLIC dependency headers to CI artifact, consumed by Windows AMD64 clang-cl and macOS ARM64 host-only native C compilation and execution. No retail game code, original user AOT, firmware or credentials in public CI.
- Windows verification proves generated host native PE32+ execution, not a standalone original-game executable; Apple ARM64 host-only C execution does not prove native ARM64 Bloodborne game.
`V391_REAL_GENERATED_LOCK_SIMD_HANDOFF.md` continues engineering record. Draft PR targets V390 branch, not compatibility/playable BBPort or BBSC Ultimate Yharnam Together.

## Critical limitations and follow-up
- Only five invented function bodies and one source-locked pinned compiler; no complete original 1.09 AOT function closure, no all-import HLE replacement, no original standalone native Bloodborne game executable, renderer/AI/physics/audio/saves/DLC/online/client/server/launcher, no original native graphics or proven performance.
- Within one backing 64-bit word, CAS is C11 seq_cst; crossing a word is **explicitly aborted** for safe incomplete x86 LOCK semantics. Guest SIMD 16/32 byte operations are multiple atomic word operations, not one indivisible transaction. Full x86 memory ordering, unaligned/cross-page locked ops and vector fault semantics need native source/owner-private validation.
- V389 quiescent reconfiguration protects *only* callers holding V386 leases. All original generated and native import/host callback paths must be instrumented and exception-safe; `longjmp`/exceptions during generated functions currently risk stranded thread-local pins. Real-game memory layouts, memory aliases/page permissions/guard faults, TLS and host services remain incomplete.
- Actual original-game legal owner files must stay on private owner-controlled storage; never publish private code, decrypted retail data or keys. A CI green status for these synthetic functions is not evidence of a playable original game.
- Continue investigating all relevant public GitHub forks/PRs/branches, preserving provenance/licensing, without claiming exhaustive internet search. Preserve native independent port as separate from playable Yharnam Together Ultimate client/server/launcher.

Next: verify CI at exact V391 head; if generated `LOCK/CAS` or 256-bit SIMD unsupported, do not fake the check or weaken assertion—record and fix source-level issue or implement an explicit negative unsupported route. Then extend generated C source AST/assembly auditing, exception-safe generated-entry lease scope and full owner-private Bloodborne 1.09 function/import and real game linker closure. Only after independent original-game boot can native GPU/streaming, gameplay, graphics/physics frame pacing, KBM/controllers/QoL and stable low-latency online be called production deliverables.
