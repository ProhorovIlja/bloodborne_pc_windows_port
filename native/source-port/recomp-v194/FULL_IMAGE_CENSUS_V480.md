# V480 — full-image inventory, separate from startup execution

An offline read-only run against the pinned CUSA03173 1.09 ELF found 205,269
distinct candidate addresses: 162,959 unwind index starts, 129,135 targets
of relative relocations into the RX LOAD, 18,444 distinct legacy constructor
targets, and 3 ELF/init/fini entry points. These groups overlap. In particular,
26,239 candidates occur only in the RX relocation group, where references
may point at constants, tables or interior locations rather than functions.

Independent Linux LLVM 19 first-instruction spot check across the entire
candidate set: 3,396 addresses did not decode, all from the RX-relocation-only
group. The 201,873 that decode are NOT confirmed functions. No decoder output,
addresses or game bytes were committed. The count is not comparable directly
with bloodborne-native's control-flow-scanner function count.

With an existing private V204 work directory, pass --v204-work to report
scanner-only and metadata-only counts, generated registry omissions, and
missing starts by source group, checking source provenance through V410/V207.
Without that directory both comparisons are null. This is source registration,
not linked coverage, and does not resolve indirect calls or runtime fallback;
V202/V309 and actual no-eboot startup runs remain separate gates.
The full V204 generator and the contiguous 1074 were not run here.
