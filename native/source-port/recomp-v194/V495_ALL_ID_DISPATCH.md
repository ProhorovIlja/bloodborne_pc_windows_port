# V495 — all-ID differential gate for the native dispatcher

V494's synthetic parity, V492, V491, census, scoped relocations, V475
startup replay and the focused rebuild gate passed on Linux and Windows.
V239's real Windows RcApi clock checks also passed. macOS jobs on that
head were queued; no macOS pass is inferred.

V495 walks every emitted ID independently of the consolidated index,
compares both native dispatchers across 16 deterministic inputs per ID,
tests absent or out-of-range read/write regions and sampled ID misses,
and checks RAX, flags, status and all bytes of the test memory. The
owner-local Linux driver statically links GCC and Clang candidates,
runs with an empty working directory and no game arguments, requires
the generated inventory count to match, and compares fingerprints.
The executable uses synthetic data and compares two implementations
using common generated bodies: it is not a differential retail opcode
oracle, runtime sandbox, or game boot test.

Prepare the private directory using prepare_v493.py and then run
probe_private_dispatch_v495.py on that directory. Only share aggregates;
never commit the executable, generated units, or original game bytes.
The new gate is wired into the existing V493 CI matrix using public
synthetic data. The whole retail gate was not executed in this change.

Reference routes checked against upstream documentation:
https://github.com/bloodborne-native/bloodborne-recomp/blob/main/docs/RECOMPILATION.md
documents a resumable owner-local AOT build; its runtime does not establish
this port's strict no-fallback property.
https://github.com/Astrr00/BloodbornePC documents bbdiff as a separate local
comparison against original instructions. V495 complements, not replaces,
that level of evidence.

Confirmed baseline: 23,048 / 179,030 (12.87%) partial AOT starts and
1,073 / 18,444 (~5.82%) contiguous constructor slots. Neither is
overall game readiness. No change to these totals.
