# V226: guarded original RcApi V4 math callback interception

2026-11-01, draft native PR #84. True goal remains a complete
native Windows Bloodborne executable without needing the original
PS4 EBOOT **at game launch**. This milestone is an opt-in library
adapter, **NOT** production runtime integration or game boot.

## Why the V224 direct entry was unsafe

Previous `shyt_math_import_v224_try_call` wrote the guest return address
to memory at `RSP - 8` without verifying that memory was mapped and
writable; `frexp[f]` also wrote through guest `RDI` without validation.
If called with invalid/corrupted CPU state, it could corrupt host memory.

V226 fixes this fail-closed:

- The old V224 unchecked function is deliberately DISABLED and always
  returns 0. Existing unit tests now use the guarded alternative.
- New `shyt_math_import_v224_try_call_checked` takes a mandatory
  host-provided guest memory checker for the entire writable return
  slot and, for `frexp[f]`, the 4-byte output integer.
- It rejects invalid stack ranges, invalid exponent pointers and
  any pointer that overlaps its own guest return address.
- Return code **+1** = handled; **0** = not a registered math target;
  **-1** = target recognized but memory UNSAFE. The caller MUST NOT
  pass a -1 into the old guest runtime or treat it as an unknown target.
  Before returning -1, it does not mutate the guest CPU or memory.
- This gate relies on a real host-provided memory map/permission
  checker; it cannot prove arbitrary guest memory is safe by itself.

## Actual upstream v4 callback route

Added `native_math_rcapi_route_v226.{h,c}`. Imports the exact
upstream `RcApi` and `BbCpu` from pinned commit
`8f31ec7c41f252730c6325d52647046baef7549f`.
An opt-in, single-install, immutable adapter copies the upstream
API and replaces only `.call`, preserving `.step`, `.tail`,
`.bail` and `.trace` pointers and `image_base`.

- Known, safe math import target: execute the V223/V222 native
  host math bridge, preserve the guest RIP/RSP return contract.
- Unknown target: call the original callback with unchanged CPU.
- Known, unsafe target: invoke a **mandatory runtime fatal fault**
  callback. That callback must terminate/trap guest execution.
  If it mistakenly returns, the adapter aborts rather than letting
  invalid memory flow into the legacy runtime.
- Install exactly once before native game threads begin; adapter and
  validation contexts stay alive until process exit. A second
  installation fails without overwriting the active API.
- Existing V224 import offsets were generated from the owner's
  original ELF at **build time**; no original game binary is read
  by V226 at runtime.

## Verifications actually completed

### Public pinned-source synthetic regression

New `test_native_math_rcapi_route_v226.c` compiled and executed
against the actual pinned public `BbCpu` + `RcApi V4` definitions.
Proved the injected callback invokes math correctly and preserves
normal upstream callbacks; errors call the fatal guest handler
without falling through to old code; legacy unchecked entry cannot
execute; disallowed guest stack/exponent pointers and return-slot
aliasing are rejected before state modification.

Both changed modules compiled locally into actual Windows x86-64 COFF
with the verified V214 SDK: V226 route **2,092 bytes**, guarded
V224 dispatch **2,375 bytes**.

Pinned public GitHub CI uses no original owner binary or generated
game C. The V226 job builds actual Zydis public headers, executes
synthetic CPU/RcApi tests and compiles both real Win64 COFF modules:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41328704574
**SUCCESS**. The affected earlier V223/V224 regression workflow was
also rerun and passed:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41328613096

### Actual private original import-table invocation

On the owner's local copy only, linked the PRIVATE V224 descriptor C
generated from all **23 real Bloodborne math import addresses** with
the V226 public adapter and real pinned upstream CPU structures. The
test invoked the `pow` math import through the **actual original
guest imported-stub offset**, using a synthetic guest CPU/stack. It
returned the correct numeric value and RIP/RSP, while an unmatched
target reached the original fallback. Result:
`V226_OWNER_ORIGINAL_23_STUB_RCAPI_MATH_ROUTE_PASS`.

This is proof of real original-derived address mapping into the
adapter, **not** a real in-game execution trace. Original import
offsets, binary and derived mapping remain outside GitHub.

## Remaining blockers

The full actual AOT runtime must explicitly pass this adapted
`RcApi` to `bb_recomp_init` after a proper guest memory range
validator and fatal fault boundary are in place. The current prototype
does not do that, nor does it translate all the existing direct AOT
calls; the upstream optimizer may bypass `.call` for direct function
targets. Full game has approximately 1,468,066 static guest callback
site occurrences (V216); math site parity V225 found 1,089 **static
named** direct import callsites, not all indirect calls.

`errno`, FENV, MXCSR, vector floating-point exceptions, game
threading, Windows API dependency closure, native rendering/audio,
assets, full linking and actual game startup are still UNSOLVED.

No game binary or original-derived objects uploaded publicly.
No Fornex deployment and no PR merge.
