# V487: one AOT dispatch entry for register and memory code

Builds V485 and V486 together behind a single native interface. Routes to
memory leaves only over bounded guest data; a known ID with an invalid
read is distinct from an unknown ID. Neither failure invokes guest code
or changes the result. Seven additional direct JMP entries close over
memory leaves in the owner-local 1.09 input. Branch closure starts at
metadata IDs, stops at eight transfers, and does not route cycles or
interior destinations. It does not attest arbitrary indirect callsites.

Private Linux x86-64: 18,439 register entries, 4,578 memory leaves and
seven aliases: 23,024 distinct dispatch IDs. Through the new common
interface, GCC and Clang static builds each matched 1,180,096 register
and defined-flag comparisons (V485 oracle) and 293,440 memory-value
comparisons (V486 leaf instructions and alias graph). Memory output flags
were checked for preservation by the candidate harness. The candidates
ran in a chroot with native executables only. The separate oracle relinks
branch displacements; short branches may use a trampoline. Synthetic
fixtures cover miss, invalid read, cycle and interior-target rejection.
No game bytes or generated retail tables are checked in.

This is a partial AOT dispatch, not the game's runtime, guest callsite
authorization, or a new ordered constructor run. The 1–1073 evidence
and full-link blocker remain unchanged.
