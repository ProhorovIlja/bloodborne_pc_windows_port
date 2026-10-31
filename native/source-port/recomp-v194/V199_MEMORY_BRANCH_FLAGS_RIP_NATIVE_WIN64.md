# V199: original full-function bbrecomp memory, JZ/flags and RIP semantics

**Both native Linux and Windows CI jobs: SUCCESS.**
[GitHub Actions 41254052483](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41254052483).

This extends successful source-port V196/V197/V198. All public CI
instructions are synthetic, with **zero** original Bloodborne executable,
game binaries or game-derived generated C published or used on runners.

## Real source-path tested

The exact original GPL-2.0+ source
`bloodborne-native/bloodborne-recomp@8f31ec7c41f252730c6325d52647046baef7549f`
with real Zydis and strictly source-pinned build-host adapter generates
**six full x86-64 functions** from a newly invented ELF, using the
normal *whole-function* recompilation path (not `--snippets`).

These six functions exercise:

- a genuine 64-bit `mov rax,[rdi]` guest-memory read
- a genuine 64-bit `mov [rdi],rsi` guest-memory write that preserves RAX
- lazy x86 `TEST rdi,rdi; JZ`, **taken and non-taken** (zero,
  positive and negative test inputs), with correct EFLAGS
- `mov rax,[rdi]; add rax,rsi` over writable memory
- `lea rax,[rip+0x39]` correctly rebased by the original
  generator to a native process's allocated image base
- a real unaligned x86-64 read `mov rax,[rdi+1]`.

All six recompiled C functions are linked with native entrypoints
into Linux ELF and Windows AMD64 COFF -> PE executables. Runtime
exercises the generated C itself, validates RAX, RSP, RIP,
EFLAGS, memory side effects and fail-fast original callback handlers
to catch unanticipated interpreter fallback. It rejects any runtime
EBOOT command-line argument. The artificial ELF is only ever read at
offline C **generation** time, never while the EXE is running.

## Actual upstream correctness problem found and corrected

The original `tools/recomp/bbrecomp.c` emits a lazy CPU flags
state (`fk/fa/fb/fr/fz/fcf`) local to its generated function.
On `RET`, its original code spills CPU GPRs and reads the return
address, **but does not flush lazy EFLAGS to `BbCpu.flags`**.
The V199 Linux regression originally FAILED after a correct JZ because
the state after RET still lacked the expected `ZF`.

`patch_upstream_ret_flags_v199.py` validates the exact original
generator's Git commit and blob
`f5032c9ead4988579e005af8a0a0ce4ba4ab66d8`,
then changes **only** the original `RET` output to append
the generator's own `FLAGS_OUT` (which invokes original `rc_flags`)
after GPR spill and before returning. This has no change to game
imports, PS4 runtime, emulator layers or shaders.

The identical original generated C tests then **passed on Linux and
Windows**, with correct taken and non-taken branch outputs and ZF
after returning from native AOT C.

This was verified on **synthetic x86 input** and is a candidate upstream
bug fix, not proof that every real Bloodborne 1.09 function requires or
passes this change. Before upstream PR or production integration,
measure full original game behavior, x86 flags edge cases, SIMD/state
restoration, and generated-code performance; some original callers may
ignore flags but whole-engine correctness must not assume that.

## Known next blockers

1. Privately run original full 1.09 PS4 executable through the offline
   scanner/recompiler; connected Drive's assets were verified but no
   original `eboot.bin` was discoverable in Drive metadata search.
2. Extend compiled-original-code Win64 test coverage to indirect
   dispatch, memory alignment, x87/AVX, thread-local state, interrupts,
   relocations, stack exception/unwind, memory safety and executable
   permissions with synthetic tests before validating original code.
3. Replace PS4 kernel/HLE imports, game GPU command stream, audio,
   movies, input, file save and streaming with actual native
   engine-level Windows implementations, not an EBOOT loader.
4. The **full game** (offline base game + DLC + chalices) must boot and
   play on clean Windows without EBOOT. Multiplayer, launcher and
   dedicated native server are secondary.

No Fornex deploy, server/client code change, PR merge or private
game file publication. PR #84 remains Draft.
