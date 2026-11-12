# Native V382 — immutable AOT-only indirect CALL/TAIL routing

Date 2026-11-12; based on V381 draft PR #111. Scope: native synthetic source/test; not a full original Bloodborne game.

## Grounded pinned upstream semantics
Pinned `bloodborne-native/bloodborne-recomp` commit `8f31ec7c41f252730c6325d52647046baef7549f`:
- `src/recomp/rc.h` RcApi version 4: `call(cpu,target,next)` pushes the guest return address before invoking a native recompiled function; the function eventually returns and updates `cpu->rip`. `tail(cpu)` uses `cpu->rip` and does not push another guest return address. `step` and `bail` were translator paths.
- `src/cpu/recomp.c` `rc_call` and `rc_tail`: exact-entrypoint lookup, push 8-byte return address for CALL, then call a compiled RcFn. No AOT entry leads to `call_other` or `tail_other` which can reach guest interpretation. That fallback is forbidden in the user's strict independent native-port target.
- Pinned native `BbCpu` layout from V194, with RSP at `r[4]`; RSP writing must preserve original x86-64 guest memory ordering and lifetime.

## What is implemented now
- `native_aot_route_v382.{h,c}`: an immutable snapshot of verified, sorted generated AOT entrypoints. Lookup uses O(log N) binary search on native absolute address; no EBOOT/SELF/ELF is opened and no interpreter or translator code is linked.
- Preparation is conditional on the V381 strict-base and a V381 admission for every function in the **supplied** table, with each `RcFunction.direct` already holding the verified native function pointer. The table is copied into private route storage to avoid subsequent caller mutations. No claim that all original 1.09 game functions exist or have genuinely passed owner-data attestation.
- Native-only CALL first resolves target, checks stack arithmetic/alignment, and calls a mandatory owner-provided **validated, atomic-failure** guest-stack writer. Only after it succeeds does it update `cpu->r[4]`, set target RIP and call the native compiled function. That function must implement the original return behavior. No arbitrary guest address is dereferenced in this dispatcher.
- Native-only TAIL resolves exact entrypoint using `cpu->rip` and invokes the native function WITHOUT another return-address push. Unknown targets fail rather than fall through to guest code.
- A process-lifetime, once-only `RcApi` callback publisher replaces CALL/TAIL atop V381 while keeping the V381 abort-on-guest `step` and `bail` callbacks. Missing targets or unsafe guest stack operations in the published path abort rather than invoke a translator. Route cannot be freed after publishing. There is no hot reload or dynamic module unload.
- `test_native_aot_route_v382.c` runs the synthetic pinned 840-byte `BbCpu` ABI, rejects missing direct slots, proof mismatches, duplicate/changed offsets, unknown targets, zero/overflow stack or rejected guest stack write, verifies native CALL push + return and native TAIL no-push, rejects route reuse or unload, and checks Unix SIGABRT when the published callback sees a nonexistent target.
- CI: Windows AMD64 clang-cl, Linux GCC/Clang ASan+UBSan, Apple Silicon host-only Clang. Green CI means only synthetic contract passes, not that original Bloodborne works on these systems.

## Remaining real blockers
- The mandatory `stack_write` callback must be connected to the future native game memory model with 8-byte atomic guest store semantics, lease/pin memory safety and GPU/CPU synchronization. Synthetic stack callbacks do not establish this.
- The V381 attestation and all AOT `RcFn.direct` slots must be verified against the *entire* licensed private original 1.09 game, including patched/import/setjmp functions. Synthetic completeness is not owner-game completeness.
- Native-only import stubs and fully native host API replacements (game loops, filesystem, saves, graphics, input/audio, network, physics, AI, scene events, DLC) remain unimplemented.
- The actual independent Windows AMD64 PE32+ / Linux AMD64 ELF64 native full game executable must be linked, booted, traced and tested without guest ELF, translator or PS4 compatibility runtime. Apple ARM64 source portability does not imply an ARM64 Bloodborne executable exists.
- No production attempt to invoke AOT code from a bootstrap should be made before genuine original AOT coverage + native host imports and zero guest fallback have been demonstrated.

## Integration route
Future V383: isolate and test real host-backed guest memory atomics and pinned allocation leases; wire the V382 `RcApi` into V245 bootstrap while preserving V226 math / V239 clock routing and preventing all unrecognized imports from reaching a translator. Later implement real game PE/ELF linker closure, rendering and gameplay parity. Keep BBPort and BBSC Ultimate playable-track branches separate.
