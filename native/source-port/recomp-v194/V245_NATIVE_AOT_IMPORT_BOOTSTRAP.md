# V245: native Windows AOT startup boundary, imports -> bb_recomp_init

2026-11-01. Separate genuine no-EBOOT Windows Bloodborne Draft PR #84.
No generated retail game code or game files are added to this public PR.

## What's new beyond previous separate host-only tests

`native_aot_services_bootstrap_v245.h/.c` is one process-lifetime
entrypoint for native Windows service integration. It:
1. Requires the original pinned `RcApi` V4 platform callbacks and correct
   original-image base, a validated 23-name math import table and two
   exact clock import offsets from *private build-time* analysis.
2. Checks clock import offsets do not alias a math import, validates
   memory/fault/pinning callbacks and checks Win32 QPC is available
   before installing any permanent route.
3. Installs existing V226 guarded math route and V239 native 1.6 GHz
   clock route IN ORDER, using ONE pinned guest-memory authority and
   pass-through for all other imported calls. Bad guest stack/pointer
   fails closed, and no unknown import is silently handled.
4. Calls the supplied actual `RcInit` (`bb_recomp_init` contract)
   **with the final composed API**, checks the returned function table
   is nonempty and bounded, and returns native registered AOT functions.
5. On an irrecoverable error after publishing the first global route,
   terminates instead of returning to callers holding partially
   initialized or dangling route memory. Install once, single-threaded,
   with a **zero-initialized services object** whose memory and callback
   contexts remain valid until process exit.

`test_native_aot_services_bootstrap_v245.c` exercises this pipeline
using a synthetic generated-code callback and the EXACT published
`bloodborne-native/bloodborne-recomp` `BbCpu`, `RcApi`, `RcFn`,
`RcFunction` and `RcInit` types. The native PE test invokes one
registered AOT C function, which uses FINAL `RcApi.call` for
`pow(2,5)=32`, `sceKernelGetTscFrequency=1.6 GHz` and
`sceKernelReadTsc`. It rejects invalid math/clock offset overlap,
ensures all callbacks used protected pins and does not load PS4 ELF.
The existing pinned-public-header Win64 workflow compiles and runs
this source alongside V222/V223/V224/V226/V236/V239.

## Critical unfinished work

- Replace SYNTHETIC fixture with the real user-owned private
  CUSA03173 **384-module** AOT export. Neither this file nor public
  CI can create that proprietary export automatically.
- Use actual verified 1.09 import slots and guest memory ownership,
  correct signed clock ABI, original game startup, native Windows
  graphics/audio/input/files/saves/network and full validation.
- Any unknown or unverified import must be explicitly reported,
  never routed to a fictional successful implementation.
- `bb_recomp_init` function-table registration alone does NOT
  guarantee that functions execute or game launches. Direct gameplay
  validation and completion of recompilation are still required.
- Last reported 54/384 Windows COFF module artifacts must NOT be
  described as complete. Do not put private source dumps into GitHub.

This stage does not use the retail EBOOT at runtime, but the *finished
standalone native port* has not been produced. CI results must be
verified for the exact branch commit. Fornex unchanged.
