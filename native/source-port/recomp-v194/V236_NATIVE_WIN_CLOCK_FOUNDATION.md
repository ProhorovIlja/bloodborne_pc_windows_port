# V236: standalone Windows-native timebase primitives (host-only)

2026-11-01. Draft PR #84 — **true native no-EBOOT Windows port**.
No original ELF or proprietary game data required at runtime or in CI.

## Why this is needed
Private import audit V221 found 6 original guest timing/clock imports
without matching BBHost registration, alongside 27 math and 1 FIOS gap.
The existing V222–V230 native math RcApi bridge already demonstrates a
host ABI approach but does not implement those time calls.

Public BBHost host-clock sources reviewed at commit
`3b0c62939395ebfd8af8b8e365d49418c53084e3` use Windows QPC
to reduce overhead versus generic cross-platform timer wrappers.
This new V236 module was implemented independently in C; it does not
copy BBHost source or assume matching PS4 ABI.

## Changed
- `native_win_clock_v236.h/.c`: Win32 `QueryPerformanceFrequency` and
  `QueryPerformanceCounter` initialized once per clock instance;
  monotonic time is relative to initialization, and there is an explicit
  target-frequency tick scaler. Fraction/seconds arithmetic is checked for
  uint64 overflow and returns an error instead of silently wrapping.
  Wall time comes from `GetSystemTimeAsFileTime` and is distinguished from
  monotonic time; UTC Unix microseconds are derived from the 1601 epoch.
- Portable mathematical conversion tests and actual Windows API smoke tests
  in `test_native_win_clock_v236.c`; Windows/Ubuntu CI workflow.

## Strict nonclaims and next integration gate
**This is NOT yet wired to 6 actual Bloodborne imported clock functions.**
Those require the exact six symbol names and signatures from the private
`imports.tsv`, verified PS4 SysV guest calling convention, correct guest
clock epoch/frequency/ID semantics, and a safe dispatch hook through the
existing `RcApi.call` and guest memory validator. Realtime host clock
is not a substitute for the game's monotonic clock. An unresolved or
unknown guest import must fail closed, not silently return success.

The module does not advance the actual full AOT compilation count (last
reported 54/384 verified COFF modules in V229), resolve PS4 subsystem
dependencies, or make Bloodborne.exe playable. It is a native primitive
that can be reused only after ABI and runtime integration tests.

## Verification
The workflow `native-v236-win-clock.yml` compiles the module as a real
Windows PE process and executes actual Win32 calls; Ubuntu exercises
portable overflow arithmetic and unsupported-OS rejection. These tests
contain no retail game assets. Check CI result for the exact head commit
before reporting success. Fornex is unaffected.


## V238: exact high-frequency clock conversion

The initial V236 `shyt_clock_scale_ticks_v236` rejected any
`remainder * target_hz` exceeding uint64, even when the *quotient*
would fit. For example, 29,999,999,999 ticks from a 30 GHz source to
1 GHz yields 999,999,999 ns, but its intermediate product exceeds uint64.

V238 uses a full unsigned 128-bit intermediate for Clang/GCC (including
clang-cl Win64, tested) and retains conservative fail-closed overflow
handling for compilers without such support. Existing result-overflow checks
remain. Regression tests include a 30 GHz fractional-second case and a
near-UINT64_MAX rate case.

Local reproducible verification of the arithmetic implementation:
10,003 fixed/random cases against integer exact-division oracle PASS;
clang-cl Windows COFF compilation PASS. This does not replace the complete
GitHub Actions run, and is still host-only, not imported into Bloodborne.
