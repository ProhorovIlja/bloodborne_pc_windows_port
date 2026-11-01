# V203: original `bbrecomp` generic function fallthrough into native AOT

**Verified both original-source Linux + native Windows AMD64 PE jobs: PASS.**

[GitHub Actions V203](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41255386312).

## Concrete actual original generator improvement

Even with V200/V201 direct native indirect CALL/JMP, the original
`bloodborne-native/bloodborne-recomp@8f31ec7` generic
`L_dispatch` block unconditionally emits a guest `RcApi.tail` at
the end of a function. This affects ordinary original x86-64
**sequential instruction fallthrough** from one compiled function
into an adjacent compiled function, with a correct guest stack depth.

`patch_upstream_fallthrough_v203.py` matches the exact pinned
`tools/recomp/bbrecomp.c` source blob and reconstructs only
the audited V199 RET-flags, V200 indirect-CALL, and V201 indirect-JMP
modifications. It modifies **one** generic L_dispatch tail emission
site in a disposable public upstream checkout.

When the generated function exits its own code region at the original
guest RSP depth, it uses the **actual original generated RcFunction
table**, through native `rc_native_find(dn)` from V200, and dispatches
directly to the function if its exact image-relative entrypoint and
writable native target are registered. An address pointing into a
function's body or to an unregistered function cannot be executed as
an approximate target.

Original intra-function dynamic-label behavior and the exceptional
non-entry-RSP `RcApi.bail` path are unchanged; unknown successor
targets still explicitly call `RcApi.tail`. This preserves the
existing behavior and alerts us to **unfinished strict-native code
coverage**, rather than inventing an incorrect guest CPU state or
silently replacing unknown branches with successful returns.

## Proof by real original-generated C (synthetic ELF only)

`generate_fallthrough_v203.py` constructs an invented ELF64 with five
whole x86 functions. It uses the same original full offline
`bbrecomp ELF functions.tsv recomp.c @offsets` code-generation
path as a real 1.09 function library, but with no copyrighted game
bytes. Two pairs are deliberately adjacent:

- Function `0x1000`: `MOV RAX,42`, **no RET**. Function
  `0x1007`: `RET`. Invoking `0x1000` must land in the next
  compiled native C function through the generic L_dispatch and
  return with RAX=42, correct RSP+8 and RIP=guest sentinel.
- Function `0x1010`: `MOV RAX,99`, **no RET**. Function
  `0x1017`: `RET`. Same validation with RAX=99.
- Function `0x1020`: independent `MOV RAX,7; RET`
  control. Direct calling other entries still works.

`whole_function_fallthrough_host_v203.c` verifies both direct
native C transitions, proper guest return semantics, **no new
guest return-address stack push**, and no interpreter/HLE callback
for registered native function entries. It then deliberately
sets the next function's native direct slot to NULL and reexecutes
`0x1000`. The negative control must call `RcApi.tail` exactly
once and **not** fake a completed return or misdispatch to code at
an approximate offset; that fallback path is tested without
executing a PS4 runtime.

Both original Linux compiler/Zydis generation and standalone
Windows AMD64 COFF `.obj` -> PE EXE and native Linux execution
are **SUCCESS**. Existing V198 SHA256 source/object reuse, tamper
detection, and one-object invalidation checks are still active in
the Windows stage.

The source-only V202 strict-native readiness gate is separately
tested: it **rejects** this output because unknown/exceptional
fallbacks remain, even if both deliberately chosen native
fallthrough paths executed without callbacks. No incorrect claim
of `strict_native_runtime_ready` is made.

## Boundaries, upstream comparison, and remaining blockers

This is real functional progress in the **broad original full-game
recompiler's C output**, but it uses only five invented x86 functions.
It is not Bloodborne's real Windows executable, gameplay, renderer
or complete offline 1.09 source recompilation.

Upstream sweep on 2026-11-01: `bloodborne-recomp@8f31ec7`
unchanged since Oct 30; `bloodborne-runtime@aa7632e` remains
Metal-focused; `Supermedo/bloodborne_pc`,
`deadinside28/bloodborne_pc`, `Astrr00/BloodbornePC`, and
`shadPS4` continue to be useful source references for system/GPU
semantics, but those Windows implementations still use a
PS4-shaped game executable and/or platform compatibility runtime
at game startup. They do not satisfy the user's independent
Windows-source-port target.

The full private retail game image remains unavailable through
the accessible Drive root (`eboot.bin` was not found in previous
metadata search); we cannot yet verify full original-code
function coverage, real native imports, dynamic branch tables,
uncommon stack layouts, original game events, graphics,
audio, file IO, saves, threading, all boss/map/DLC/chalice paths,
or clean standalone Bloodborne.exe boot.

The next gate is to eliminate remaining original-generator
`tail/bail/step/call` fallback sites **with correct control flow**,
not by disabling V202, and to validate the actual user-owned
original 1.09 executable strictly **privately**, at build time
only. No original game data may be published in GitHub.

No production deployment, Fornex/YT server modification, merge,
private game file upload or release. Draft PR #84 remains native
Windows-port research.
