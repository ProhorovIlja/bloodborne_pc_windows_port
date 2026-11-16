# V447: standalone retail startup first

Target: independent Windows x64, Linux x86-64 and macOS arm64 runtime. The
original executable may be an input to private offline preparation, not to
the shipping runtime; no renamed or embedded PS4 executable or fallback to a
PS4 loader, interpreter or JIT. Game data still comes from the owner's copy.

V446 evidence: corrected callbacks 1–89 returned on private Linux x86-64.
Corrected callback 90 entered the registry path and stopped before insertion.
The earlier V432 order is not an interchangeable end-to-end startup prefix.
The isolated pattern batch skipped nonmatching callbacks; do not add those
counts to the ordered prefix.

V447 adds a private-only aggregate audit batch. Use repeatable
`--body ORDINAL EXTENT` with independently reviewed extents. The report
contains ordinal and transfer counts, no addresses, paths, or game bytes.
A linear census does not establish closure or execute the game. The next
runtime checkpoint is completing registry lookup/allocation/insertion and
observing the checked outer return of callback 90 on the same ordered state.

Acceptance: retail entrypoint reaches main, title screen starts offline, a
new game loads a real area, accepts input, saves, shuts down and reloads.
Run from an isolated directory with assets and the host build only; verify
no console executable/module or emulator fallback is loaded. Report this
per OS, separately from synthetic CI. Online, launcher, and new features
are outside this gate.
