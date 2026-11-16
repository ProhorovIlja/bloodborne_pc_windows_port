# V483 — batch lowering of register-only leaves

Owner-local CUSA03173 1.09: scanned 179,030 distinct metadata starts and
emitted 11,011 independent host C functions. Of those, 7,761 preserve RAX,
2,990 materialize an immediate, and 260 copy a register (with x86 width
semantics). None are constructor entries. No arbitrary relocation target was
used as a seed. Exact accepted forms end in a plain RET; memory, branches,
calls, imports, stack-adjusting RET, and flag-changing operations are not
lowered by this pass. The caller still owns return control flow and guest ABI.

Two statically linked Linux x86-64 candidates (GCC and Clang) ran from a
chroot holding only host binaries. Both matched all 176,176 RAX outputs from
a separate oracle executing the extracted original leaves with identical
input registers (16 cases per leaf, 352,352 comparisons total). This tests
isolated RAX semantics, not runtime dispatch, reachability, or complete
game execution. Generated C, IDs, original bytes and traces remain local.

The CLI authenticates the input against a supplied digest, refuses RX
relocations, and writes only into a fresh owner-local directory outside Git.
The build can reconcile its private ID list with a later complete emitter
manifest: do not add these numbers to upstream scanner/emitter counts.
bloodborne-native's build_library.py is the broader resumable AOT reference;
its runtime is not used in this pass. V483 is not integrated into V204 or
the ordered startup harness; no constructor advance or full link claimed.
