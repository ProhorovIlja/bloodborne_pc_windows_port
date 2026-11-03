# V221/V222: Real original Bloodborne import coverage and initial native PC math

2026-11-01 continuation of draft PR #84. Source owner data remains private.

## V221: actually registered BBHost handlers, not just import names

Original user-owned CUSA03173 decrypted Bloodborne 1.09, extracted
`scan/imports.tsv` on a PRIVATE machine, compared against public
BBHost's HLE registrations from `src/hle/*.cpp` at Git SHA
`8d8f07db3bad61dcdbf11511c9d34acfdfa162cd`.

| Actual source-backed category | Count |
| --- | ---: |
| Private Bloodborne imported stub rows | **660** |
| Unique BBHost public registered HLE names | **672** |
| Original stub rows with matching HLE registration | **626** |
| Original stub rows without matching HLE registration | **34** |

**Breakdown of the 626 matching registrations by source module:**

| BBHost public HLE module | Original matched imports |
| --- | ---: |
| libc | 155 |
| system | 131 |
| pthread | 64 |
| gnm | 50 |
| net | 41 |
| np_matching2 | 27 |
| http | 26 |
| kernel | 21 |
| audio | 20 |
| dialog | 18 |
| avplayer | 16 |
| fios | 16 |
| fs | 14 |
| ajm | 12 |
| video | 8 |
| np_signaling | 7 |
| **Total** | **626** |

Original-name gap classification, done privately and only printed here
as aggregate counts: **27 mathematical imports, 6 timing/clock
imports, 1 PS4 FIOS sync import**. Among 27 mathematical imports,
**23** have readily typed standard C math-library counterparts;
**4** vendor-specific names (`_Log`, `_FLog`, `_FCosh`, `_FSinh`)
require their actual binary signatures and semantics to be researched
before bridging. The 6 timing imports need PS4-compatible time and
frequency/clock-ID semantics, not naive system clock substitution.
The FIOS import needs actual filesystem synchronization semantics.

This is stronger than V220's **659 matching PLT symbol-name records**:
V220 measures names listed in a PLT map, while V221 looks for
registered handlers from actual BBHost C++ source. **A registration
does not prove implementation behavior, ABI correctness, or runtime
availability**. Some registrations can be compiled conditionally or
implement deliberate no-op behavior. BBHost `bind_import` falls
back to `hle_make_stub` when no registered handler exists.
No claim of 626 fully implemented system calls is made.

New `compare_private_imports_bbhost_hle_v221.py` is a bounded,
private-safe source/TSV analyser that prints **only aggregate counts
and source-module categories** and never private addresses/names.
A public BBHost registration TSV and its GPL license were bundled
as a 17-KB GitHub Actions artifact for **local-only** private
comparison; proprietary game data never entered GitHub CI.

V221 Windows and Ubuntu syntax/synthetic checks and pinned actual
public HLE extraction all PASS:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41324904221

## V222: original authored host-side math bridge (23 functions)

Implemented `native_math_shim_v222.h/.c` with typed ordinary
C/Win64 host wrappers for 23 standard scalar math functions:
`atan2, fmod, acos, tan, asin, atan, exp, pow, frexp, exp2, ldexp`
and their 12 requested float counterparts including `tanhf`.
The four vendor-specific math entry points remain **unimplemented**
pending genuine signature research. Code does not copy BBHost or
other GPL HLE implementations.

`test_native_math_shim_v222.c` exercises finite constants,
domain errors (NaN), overflow (infinity), negative-zero sign,
and `frexp` exponent output. On Linux the native host test
executes; on Windows the actual target is compiled into AMD64
COFF and verified by its machine header.

V222 CI PASSED both jobs:
https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41325324844

### What this does NOT establish

- Host math exports are **not yet bound** to the original game's
  23 import slots or AOT guest call sites; SysV-to-Win64 argument,
  floating-point register, `errno`, IEEE exception and x87/SSE
  ABI behavior are NOT proven.
- The four special math functions and six clocks + one FIOS import
  are not silently stubbed to success.
- Entire original game Windows COFF output currently has **50/384**
  manifest-verified source modules (V219), but original guest runtime
  callback sites and system/engine initialization remain.
- No independent native Windows Bloodborne.exe launch, fully
  functional rendering/audio or gameplay session has happened.
- No public game assets/ELF, no Fornex changes, no merges.

Next priority: verify actual PS4 import calling convention and
typed ABI for 23 common math functions, then provide a *runtime-free*
native import bridge that plugs into AOT dispatch while preserving
original saved state. Independently implement timers and FIOS with
tests, rather than marketing the exported host math helpers as a game.
