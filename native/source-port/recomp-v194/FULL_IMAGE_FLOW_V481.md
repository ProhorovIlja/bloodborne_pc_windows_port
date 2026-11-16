# V481 — direct control flow across the owner-local 1.09 image

Linux LLVM 19, CUSA03173 decrypted ELF. Seeds were 179,030 distinct IDs
from unwind, constructor, and ELF/init/fini metadata; relocation targets
were compared afterward, never treated as automatic starts. The walk
recursively follows encoded direct calls, jumps and conditional targets.
Call continuations are conservatively included without proving return.

- 9,940,194 decoded instructions, 40,934,495 instruction bytes.
- 179,025 seeds at decoded starts; 602 new decoded direct-call target IDs
  not present among the seeds. IDs are not independently verified functions.
- 439,358 direct call, 187,188 direct jump, and 804,976 conditional sites.
- 156,180 indirect call and 15,742 indirect jump sites; targets not resolved
  by this pass. Seven direct edges leave the mapped RX range; seven
  control encodings were unclassified.
- 11,300 failed decode starts and 42 interior/overlap arrivals. These are
  analysis diagnostics, not one-to-one counts of missing functions or bugs.
- 102,893 of 129,135 relocation target IDs coincided with decoded starts;
  26,242 did not. Decoding alone is not sufficient to permit dispatch.

The count depends on the seed set, decoder and stopping policy. A real
LLVM fixture and synthetic overlap/rejection fixture passed locally.
The scanner emits aggregates, not code, pointer lists or game bytes.
No V204 generation, native link, strict startup or gameplay was performed
by V481. This does not change the last contiguous constructor evidence.

Independent comparison: bloodborne-native/bloodborne-recomp uses Zydis
and its own graph and table recovery. Its published instruction/function
totals cover a different input scope and must not be subtracted from these
counts. Its AOT emitter and switch recovery are useful offline comparators;
its translator/interpreter is not a strict runtime fallback for this port.
