# Native V202: original full-generator C dependency gate

**Verified: real upstream-generated C is audited before declaring a game
independent of the PS4 guest runtime. Linux + Windows CI SUCCESS.**

[GitHub Actions V202](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41254985816).

## What changed

This milestone is a deliberate **negative readiness gate**, NOT a claim
that all interpreter fallbacks have been removed.

`audit_native_runtime_v202.py` scans real whole-function C generated
offline by exact-source-pinned
`bloodborne-native/bloodborne-recomp@8f31ec7c41f252730c6325d52647046baef7549f`,
not C manually substituted for the generator. It checks both the
`recomp.c` function table and all `recomp_XXXXX.c` shards, uses a
real C string/comment-aware lexer so commented-out or quoted examples
cannot mask or inflate counts, and reports **aggregates only** of
generated invocations to `rc->step`, `rc->call`,
`rc->tail`, `rc->bail`, and `rc->trace`.

`build_incremental_coff_v198.py --require-no-guest-runtime` now
integrates this audit **before** generating, caching, or linking any
native Win64 COFF. Any remaining such invocation yields a deterministic
rejection. It does not silently create an EXE that still requires
an interpreter/HLE helper on an untested path.

## What the public regression actually established

Generated input: **five entirely invented x86-64 whole functions**
from the **original** public bbrecomp compiler, with real Zydis,
including V199 x86 lazy flags flush and V200/V201 direct native
indirect CALL/JMP dispatch.

The real generated C (two compiler input files) contains
**16 original fallback call sites in source**:

| Invocation class | Count |
| --- | ---: |
| `rc->tail` | 8 |
| `rc->bail` | 8 |
| `rc->call` | 0 |
| `rc->step` | 0 |
| `rc->trace` | 0 |

Some of these sites are cold paths unexecuted in the synthetic known
function tests. The existing host's fail-fast callbacks verify they
are **not executed** for these chosen values. Nevertheless, **they
are still part of the object code and potential execution behavior**.
A clean native game may not rely on their being unreachable without
proof or on a separate PS4 guest implementation at runtime.

The original-generator output is therefore **correctly refused** in
strict mode, while the separate *research mode* still compiles,
links and executes the synthetic Windows PE EXE and Linux native
executable. Both jobs passed:

- Linux original full generator + Zydis: PASS. Lexical self-test: PASS.
  Real C audit: 16 fallbacks. Strict rejection: correctly returns 3.
- Windows real AMD64 COFF builder: PASS. Strict mode blocks the
  fallback-laden generated C BEFORE compiling objects, with code 2
  and an explicit error. Ordinary research-mode compilation,
  original AOT direct/indirect tail function execution, incremental
  caching, and deliberate COFF-corruption detection: PASS.

No copyrighted game code/EBoot/PS4 binaries were uploaded. The audit
can run privately over genuine original-generated 1.09 source
shards when the user-owned original executable is accessible.

## Usage on strictly private game-code output

```powershell
python native/source-port/recomp-v194/audit_native_runtime_v202.py --generated-dir "D:\PrivateNativeAOT\generated"
python native/source-port/recomp-v194/audit_native_runtime_v202.py --generated-dir "D:\PrivateNativeAOT\generated" --strict
```

The strict flag rejects any remaining callback even if our synthetic
test never reached it. The compiler's
`--require-no-guest-runtime` enforces the same rule before COFF
objects are produced. All `recomp*.c` and `.obj` game-code outputs
must remain private, outside Git worktrees; the audit does not copy
C or dump symbol addresses.

## Important limits

This **does not** show that the code has no guest CPU ABI, unsupported
instructions, PS4-shaped data formats, imports, callbacks through
other names, guest traps, or incompatible GPU/audio/OS services.
It checks only the five named `RcApi` legacy callback sites and does
not prove dead-code elimination or program-wide control-flow
reachability. Calling it "a completed native port" would be wrong.

The next real code work is to remove or explicitly convert the
remaining tail/bail/step/call paths, establish imports and native
function coverage over the **full private original 1.09 executable**,
and implement *game-engine-level* native Windows graphics/audio/input/
save/thread/asset streaming. The private Drive currently exposes game
assets, but a root `eboot.bin` was not discoverable in its index.

## Upstream update sweep (2026-11-01)

- `bloodborne-native/bloodborne-recomp` still at
  `8f31ec7`, 2026-10-30. No open upstream PRs.
- `bloodborne-native/bloodborne-runtime` at `aa7632e`,
  2026-10-31, documents Metal-only shader compilation.
- `visy/bloodborne_pc_windows_port`: runtime code and graphics
  donor, latest checked commit `4231148`, 2026-10-31. Has a
  guest game executable + PS4-shaped loader at runtime.
- `Supermedo/bloodborne_pc`: `b480526`,
  2026-10-30; Windows launcher + Vulkan runtime donor.
- `deadinside28/bloodborne_pc`: `0fc2921`,
  2026-10-28; shared memory pipeline and GPU research donor.
- `Mrsuss60/bloodborne_pc_windows_port`: `b62051d`,
  2026-10-31, shader_recompiler CFG modernization relevant
  to future shader/geometry port.
- `shadps4-emu/shadPS4`: `55a97e4`,
  2026-10-31, open shader/PM4/OS fixes reference only.
- `droogie/bbhost`: `3a9248f`,
  2026-10-26, performance/stability reference.

All alternative game-execution builds examined still need the
PS4 guest executable and/or game-shaped runtime at launch. Their
specific bug fixes may be useful, but the **final project target**
is an independently compiled Windows game without them.

No merge, production game executable, private original asset upload,
live Fornex deploy, Yharnam Together server modification or release
was done. Draft PR #84 remains native game-port research.
