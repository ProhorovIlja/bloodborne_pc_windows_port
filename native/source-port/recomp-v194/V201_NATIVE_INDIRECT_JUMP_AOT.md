# V201: native indirect JMP to original-generated Windows AOT function

**Real Linux + real Windows x64 PE tests PASS:**
[Native V201 original bbrecomp indirect jump CI](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41254657620).

This builds on [V200 native indirect CALL](V200_INDIRECT_CALL_NATIVE_DISPATCH.md)
and the earlier original full-function V199 lazy EFLAGS correctness fix.

## Problem

The exact upstream source `bloodborne-native/bloodborne-recomp@8f31ec7`
generates `dn = t; goto L_dispatch` for **every** x86 indirect JMP,
including a register target or a pointer from a vtable. Even if the
destination is already in the compiled native `RcFunction` table,
its generic dispatch route can fall into `RcApi.tail/bail` rather
than executing the native target directly. This is not suitable as the
final architecture of a standalone Windows game.

## Implemented, source-verified change

`patch_upstream_indirect_jump_v201.py` strictly validates original
`bbrecomp.c` commit + blob SHA, reconstructs the exact previous
V199 EFLAGS and V200 indirect CALL source adaptations, and refuses
all unrecognized upstream source mutations. It edits exactly one
original indirect-JMP emission site.

Generated C treats a computed JMP as follows:

1. Compute the destination address once.
2. If it is **inside the current function**, preserve the original
   `dn; goto L_dispatch` path for within-function computed labels
   and potential jump tables. This is a correctness preservation rule.
3. Otherwise spill x86 register state and commit pending x86 EFLAGS,
   update the true guest RIP, and check whether the guest RSP equals
   the original function entry stack pointer.
4. If at the normal entry stack depth, use V200's private
   **O(log n), exact-entrypoint-only** `rc_native_find` against the
   generator's own complete `RcFunction` table. If the target exists
   and its native dispatch pointer was initialized, jump into that
   exact generated C function directly, with **no CALL stack push**.
5. Unknown / unavailable targets still use explicit original
   `RcApi.tail`, while non-entry-stack layout calls
   `RcApi.bail`. Both remain fallbacks to replace or resolve before
   delivering a strict EBOOT-free game. No unknown native code address
   is guessed, cast or executed.

## Actually tested original-generated C on both operating systems

The source fixture is a **fully invented** ELF with five whole x86-64
functions, compiled by the original full `bbrecomp` with real
Zydis and actual source-locked Windows rc.h:

- `JMP RAX` directly into native compiled `mov rax,42; ret`.
- `JMP QWORD PTR [RDI]` using a genuine 64-bit pointer slot to
  compiled `mov rax,99; ret`.
- `MOV RAX,RDI; JMP RAX` using a second registered native target.
- Direct independent invocation of both destination functions.
- Exact-entrypoint lookup returns NULL for interior/unknown offsets
  and when the direct slot is uninitialized.
- Original native guest RSP and final RIP verified after the target
  function's RET; an indirect JMP **must not** write another return
  address onto the guest stack.
- All interpreter/HLE callbacks are intentionally configured to fail
  the test if reached, and **were not reached**.
- V198 incremental AMD64 COFF object cache tests remain active:
  no-change reuse, single-source invalidation, and deliberate object
  tamper with a still-valid COFF header forces one rebuilt object.

The generated C and resulting independent AMD64 PE execute without any
runtime PS4 ELF, EBOOT, PS4 loader or private game assets. The **original
five function bodies are invented** and not actual game code. No original
Bloodborne binaries were uploaded to CI or shared.

## Remaining native game port blockers

- **The entire original private 1.09** guest image, all functions and
  imports have not been compiled to Windows PE using this chain.
  The connected Drive's game assets are present but a separate
  original `eboot.bin` was not discoverable from metadata.
- External imported functions, unknown jump targets, interpreted
  instructions, unusual stack layouts and Windows SEH/TLS still
  require design and actual-game replay tests.
- Native engine-level Vulkan/DirectX graphics (not a permanent PS4
  GNM translation layer), audio, IO, file streaming, save pipeline,
  physics and original DLC/chalice/NG+ need whole-game tests.
- Only then should seamless P2P multiplayer, native server, launcher,
  mods/QoL and user-facing packaging return to the critical path.

Native PR #84 remains Draft. No Fornex/YT server deployment, merge,
game uploads or claims of playable standalone Bloodborne.
