# V239: first actual RcApi.call integration for Windows guest clocks

2026-11-01, independent **no-runtime-EBOOT native Windows** track PR #84.
Previous V236/V238 supplied only Win32 host timing primitives; this
version supplies a compositor for the genuine pinned public
`bloodborne-native/bloodborne-recomp` RcApi V4 call interface.

## Verifiable source facts

- `RcApi::call(BbCpu*, target, next)` invokes a guest function that
  returns at `next`, with the return address not yet on guest stack.
- The existing V226 math RcApi shim already intercepts 23 build-time
  mapped math targets, with validated guest memory and allocation pins.
- BBHost's `src/hle/kernel.cpp` registers `sceKernelReadTsc`
  (returns monotonic guest 1.6 GHz ticks) and
  `sceKernelGetTscFrequency` (returns 1,600,000,000).
  A clock function's presence in BBHost does not establish that the
  current private game imports both or that any unverified clock ID
  has matching semantics.

## What is implemented

- `native_clock_rcapi_route_v239.h/.c`: opt-in, immutable, single
  pre-worker-thread RcApi wrapper that accepts the EXACT imported image
  base + two privately discovered offsets supplied at build time,
  without opening original PS4 ELF/EBOOT at runtime.
- For an exact known clock target: hold a guest allocation lease,
  validate writable guest return stack slot, obtain 1.6 GHz host QPC
  elapsed counter or its frequency, write `RAX` and return to `next`.
  Unknown targets forward unchanged through the prior RcApi. This can
  chain AFTER installing the V226 math route, with no duplicated clock
  and math sequence domains.
- A malformed guest call fails closed through mandatory fault callback
  after pin release, never through an unchecked legacy import.
- `test_native_clock_rcapi_v239.c` uses real public `BbCpu`,
  `RcApi` layout and synthetic offsets to test clock interception,
  untouched unrelated calls, pin-failure and invalid guest stack.
- `.github/workflows/native-v239-clock-rcapi.yml`: pinned public
  recompiler headers + real Win64 PE compilation/execution, no game
  bytes. CI outcome still has to be checked.

## Crucial missing build/run integration

1. Confirm exactly which of the original private `imports.tsv` names
   are imported and their effective fully relocated image offsets.
   Never invent those offsets or write a game-specific import table
   to public GitHub.
2. Chain *in the actual native executable pre-worker initialization*:
   original RcApi -> V226 pinned math route -> V239 pinned clock route,
   then pass the final API to `bb_recomp_init`; provide a real guest
   memory validator, a fault boundary and lifetime-stable route contexts.
3. Verify the game's precise TSC epoch, interval, rollover and
   scheduler behavior under original private functional traces, and
   resolve remaining clock-id and FIOS calls.
4. Run on the private user's actual 1.09 AOT game code with correct
   Windows graphics/audio/input and full startup, retaining no original
   eboot.bin as a runtime requirement.

This is the first standalone callback bridge component for two clock
semantics, **not** completed step 2, the full native port, a playable
exe, or evidence of all 384 Windows COFF modules. There is no Fornex
server change and no proprietary binaries in public CI.
