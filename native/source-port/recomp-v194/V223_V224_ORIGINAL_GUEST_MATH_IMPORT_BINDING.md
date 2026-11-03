# V223/V224: guest ABI math dispatch and actual original Bloodborne imported slots

2026-11-01. Work in **Draft native PR #84** on a real owner-supplied
decrypted PS4 ELF. Target is a complete native Windows executable
that does NOT need the original EBOOT at startup. Nothing here is
being claimed as completed game startup or a working in-game
replacement yet.

## V223 verified API and original CPU layout

Public pinned upstream:
`bloodborne-native/bloodborne-recomp@8f31ec7c41f252730c6325d52647046baef7549f`.
Its `src/cpu/cpu_internal.h` defines `BbCpu` register order,
XMM vectors and guest stack. `src/recomp/rc.h` defines `RcFn` as
`void(BbCpu*)`, and `RcApi.call` as `(cpu,target,next)` with the
return address NOT pushed yet.

New source: `native_math_guest_bridge_v223.h/.c`.
It uses the **actual original upstream BbCpu definition**, not a
made-up layout. Explicitly marshals:
- double/float arguments from XMM0/XMM1 (`cpu->v[0/1]`);
- mixed FP/pointer `frexp[f]` from XMM0 and guest RDI;
- mixed FP/integer `ldexp[f]` from XMM0 and guest RDI;
- typed result into guest XMM0, leaving the other vector upper lanes
  intact in this bridge;
- guest RET from the existing return slot at RSP, setting guest RIP
  and increasing RSP by 8.

The host math functions remain V222 original-authored Win64 C
wrappers, NOT copied from BBHost. Exactly **23** original math names
resolve through `shyt_guest_math_v223_find`. Unsupported names
(`_FLog`, FIOS etc.) fail closed with NULL; never return success
for an unknown import.

Synthetic tests against the **actual pinned BbCpu header** exercised
mixed floating/integer/pointer ABI, two FP args, actual guest stack
return state, GPR/flags preservation in tested cases, and exact lookup
of all 23 handlers.

Local real public-header build:
- `v223_bridge.obj`: **7,117 bytes**, x86-64 Win64 COFF.
- No game binary in GitHub CI.

## V224 exact PS4 original imported-slot mapping, build-time only

Read PRIVATE actual `scan/imports.tsv` produced by V213 from the
owner's full 93,667,640-byte decrypted CUSA03173 game. All **23**
supported math import names exist and point at **23 different guest
stub addresses**, checked privately. The actual addresses are NOT
published.

`build_private_math_imports_v224.py` writes an owner-private C
descriptor table, refusing to output inside any Git worktree.
The generated table is **build-time source data** and needs no
original EBOOT for runtime lookup.

`native_math_import_dispatch_v224.h/.c` binds exactly 23 unique
offsets/names, translates offsets relative to an explicit guest
image base, and handles `RcApi.call(cpu,target,next)` style math
calls: pushes `next` on the guest stack, dispatches V223's
typed math function, and pops via the guest return. Unrecognized,
duplicate, overflowed or missing bindings fail closed.
This remains an **isolated dispatch candidate**, not yet installed
into the full runtime `RcApi.call` and not a completed EXE.

Actual PRIVATE Win64 compilation of the **real original-derived
23-row mapping**:
- `private_original_math_descs.obj`: **1,308 bytes**, AMD64 COFF,
  5 sections.
- `v224_dispatch.obj`: **1,778 bytes**, AMD64 COFF,
  6 sections (public-source code).
- Actual `v223_bridge.obj`: 7,117 bytes (public-source code).

Synthetic test confirms no CPU state change on unknown target or
zero return address, correct guest `pow(2,4) -> 16` dispatch from
a simulated game import stub, RSP/RIP return and duplicate mapping
rejection. The REAL original imported-slot generator passed on
the owner's private game and emitted a 23-entry source table,
compiled locally to Win64 COFF. No original-derived source,
binary, guest addresses or hashes are sent to public GitHub.

Public CI uses only pinned/public upstream and **invented** import
offsets, checks real BbCpu state semantics and actual Windows
cross-target COFF for both V223 and V224. CI green:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41326929338

## Critical limitations / next step

- Full native runtime still has ~1,468,066 static guest callback
  sites across 383/384 generated C files (V216). Neither V223 nor
  V224 has yet been installed as a production `RcApi.call` hook.
- The caller must guarantee RSP and guest pointer arguments refer
  to valid writable mapped memory. Pointer bounds are not yet
  validated inside this early bridge; real import integration MUST
  add guest-memory/address-range safety and proper exception paths.
- Host vs PS4 `errno`, `fenv`, MXCSR/SSE flags, nan payload,
  rounding and ABI corner cases have not been proven equivalent.
- The original game AOT table's 790 omitted functions (660 imports,
  130 setjmp callers) are NOT automatically resolved by this work.
- Source-derived math import addresses must stay PRIVATE, and
  all game inputs remain local. Fornex unchanged, PR remains Draft,
  no independent Bloodborne.exe boot or playable mod change.

**Next:** audit and integrate the math dispatcher with the actual
`RcApi.call` callback route in a controlled, original-game native
runtime harness, with guest stack range checks, differential numeric
tests, and no original EBOOT loader at launch. Independently implement
6 timing imports and FIOS sync.

## V225: actual *full original game* direct call-site target parity

2026-11-01, owner-private local full V213 AOT scan. New bounded
`audit_private_math_calls_v225.py` cross-checks actual source
direct-call targets in every `recomp*.c` file against the
private `scan/imports.tsv` and the exact 23 V223/V224 names.
No function offsets, original code, private paths or guest bytes
are printed or committed to GitHub.

| Fully private original-game check | Observed |
| --- | ---: |
| Real generated original C files scanned | **384** |
| Static direct math import calls with named targets | **1,089** |
| Guest target expressed as image base + import offset | **1,089** |
| Of 23 supported math import names encountered | **23** |
| Target mismatches against the REAL scanned import offsets | **0** |
| Unsupported/non-direct cases among these named math calls | **0** |

This is a direct source-level demonstration that the V224 import
offset table agrees with ALL **1,089 statically identifiable,
direct, named math import calls** in the full AOT output. It is
not a count of runtime call frequency, nor evidence for indirect
calls that cannot be annotated statically. No original game code
was added to public source/CI.

A private 23-row original-derived C table also compiled locally as
**1,308-byte AMD64 Windows COFF**. V223 math bridge compiled as
**7,117-byte AMD64 COFF** and V224 import dispatch as
**1,778-byte AMD64 COFF**. The original-derived source/object
remains private. All 23 import addresses were present and distinct
in the real original scan.

Public Windows/Ubuntu V225 CI validates parser invariants against
invented source and corrupted offsets ONLY:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41327412501

**Still NOT installed in actual `RcApi.call` game runtime**;
target and memory safety must be proven before real gameplay,
especially a validated writable guest stack. No game boot,
renderer, audio, saves or full no-guest-runtime claim follows.
The 1,468,066 static callback-site count from V216 is unchanged
by adding these source-only bridge components.
