# V200: direct native indirect x86 CALL via original full bbrecomp

**Test result:** Linux and Windows AMD64 PE **SUCCESS** in
[GitHub Actions V200](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41254504378).
Both jobs ran the exact original pinned upstream generator with genuine Zydis,
generated C for five whole-function synthetic x86-64 bodies, then executed
those C functions on both native platforms, with zero runtime EBOOT.

## Problem solved for translated functions

`bloodborne-native/bloodborne-recomp@8f31ec7` directly calls a compiled
function when the x86 `CALL` instruction names an immediate known target,
but **ALL** register/pointer indirect CALLs were emitted as
`rc->call(c, t, next)`. This means vtables, function pointer fields and
callback code depended on the external CPU/runtime dispatcher even if the
callee was already natively compiled. The project's ultimate target is a
self-contained Windows game without that guest CPU path.

The source-locked adapter
`patch_upstream_indirect_call_v200.py` validates the exact original
`tools/recomp/bbrecomp.c` blob
`f5032c9ead4988579e005af8a0a0ce4ba4ab66d8`,
allows only the previously source-pinned V199 RET EFLAGS correction,
and transforms precisely three generator sites:

1. The generated `recomp_<window>.c` references a new native
   `rc_native_find(uint64_t)` function.
2. The generated `recomp.c` exports that function. It performs an
   **O(log n) binary search** on the **original compiled RcFunction
   table**, indexing the exact source image-relative function
   entrypoint offset. It returns the registered native `RcFn` only if
   the offset exactly matches and the writable `direct` slot is
   initialized. Interior addresses, unmapped addresses and uninitialized
   slots produce NULL; no guessed nearest function is used.
3. Indirect x86 CALL emission now computes target **once**, spills
   CPU state, commits pending x86 lazy flags (`FLAGS_OUT`), checks
   the direct compiled entry, then pushes the original guest CALL
   return address, updates guest RIP and invokes the matching
   generated C function **directly**. It then reloads the x86
   register/flags state. Unknown/import addresses fall back to the
   original `RcApi.call` for explicit attribution, not a silent
   misdispatch. This fallback must be eliminated or safely handled
   before the final strict EBOOT-free game can ship.

## What the original code genuinely executed

Five entirely invented x86-64 whole-function bodies, compiled through
the *original full generator* with real Zydis:
`CALL RAX; RET`, `CALL [RDI]; RET`, `MOV RAX,42; RET`,
`MOV RAX,RDI; CALL RAX; RET`, `MOV RAX,99; RET`.

The independent Windows and Linux host linked against the actual
generated C and `RcApi v4`. It tested:

- CALL register to known native entry 0x1020, returns 42.
- CALL via 64-bit pointer slot to native entry 0x1050, returns 99.
- MOV RAX,RDI then CALL register to native entry 0x1050, returns 99.
- Proper guest return addresses written by CALL and two RETs
  pop into the original guest caller's sentinel.
- Exact-entrypoint lookup and rejection of interior or outside
  image addresses and `direct=NULL` slots.
- All interpreter/runtime fallback callbacks are wired to fail
  the synthetic test and were **not** invoked.
- Native Windows build uses V198's incremental AMD64 COFF module
  compilation and SHA-256 verified object cache. No ELF, EBOOT,
  Orbis loader or PS4 emulator is loaded by the running PE EXE.

This does **not** compile Bloodborne's original game or implement all
native engine imports. It is a real native C dispatch improvement that
scales to the full function table but remains insufficient for game
boot. Indirect JMP, exceptions, imports, native renderer/audio, and
the entirely private original 1.09 recompilation are separate tasks.

Never include private game or game-derived code in GitHub runners.
Native PR #84 stays draft, no live Fornex/YT server or launcher change,
no merge or product release.
