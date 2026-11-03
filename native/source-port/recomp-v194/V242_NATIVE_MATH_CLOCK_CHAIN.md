# V242: one actual Windows-native RcApi chain for math and clocks

2026-11-01. True no-EBOOT Windows port, Draft PR #84.

## Incremental integration, not a toy duplicate

Existing V226 guarded 23 math import names via the genuine upstream
`RcApi.call` and `BbCpu`. V239 added two explicit clock functions
through the same contract using V236/V238 Windows QPC. But neither
earlier standalone test exercised both routing layers in sequence.

V242 adds `test_native_math_clock_chain_v242.c`:
1. Create pinned PUBLIC `bloodborne-native/bloodborne-recomp`
   `RcApi` V4 with synthetic import offsets and valid guest stack.
2. Install V226 pinned math route (real `pow(2,3)=8` and guest FP ABI).
3. Install V239 Win32 clock route on top of the existing math RcApi.
4. Invoke **only the final API** for math, TSC 1.6 GHz and TSC
   frequency, then an unknown target that must fall back to original.
5. Deny guest memory access and assert both known math and clock
   targets produce a guest fault AFTER releasing their allocation pin.
   The failed calls must never execute the original unchecked callback.

The existing `native-v239-clock-rcapi.yml` now compiles and runs this
real Windows PE from V222, V223, V224, V226, V236 and V239 source plus
pinned public headers. Build-time fixtures use synthetic addresses;
no private PS4 executable, game code or protected files enter CI.

## Remaining actual-game milestones

- Private, exact original 1.09 import names/offsets, with a code-only
  build-time registration table (not runtime ELF or public assets).
- Own guest allocation validator and pin hooks for the actual AOT
  memory arena; genuine fault boundary with trusted longjmp lifetime.
- Actual user-owned 384-module AOT compilation/link and final
  `bb_recomp_init` registration into the game startup path.
- Remaining guest clock calls/FIOS, graphics/audio/input/resources,
  runtime correctness, save/area traversal/boss test, native online.

**Do not call a standalone RcApi chain the completed no-EBOOT port.**
CI success for the latest commit requires independent verification.
Nothing deployed to Fornex or uploaded proprietary files.
