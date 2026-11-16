# V491 — bounded writable leaves

Exact RDI-relative MOV stores, no additional guest operations, plain RET.
Widths 1/2/4/8, displacement sign extension, REX.W immediate sign extension,
exact-ID lookup, and fail-before-write semantics. The caller supplies the
region and owns guest register state, RET, stack and synchronization. This
is not a guest memory manager; concurrent visibility/atomicity is not asserted.

Owner-local CUSA03173 1.09 ELF, SHA-256 matched the pinned 1.09 identity.
Independent local metadata extraction: 179,030 seeds, 18,444 constructor
slots. V491 classifier emitted 951 distinct store IDs, none constructors.
Private Linux x86-64 run: GCC and Clang native shared libraries each
matched 60,864 whole-buffer comparisons against exact original sequences
in a separate oracle path in the test process, and rejected 1,902 invalid
writes with the entire buffer unchanged. No retail bytes or generated
tables are committed. The test is not an isolated full-game executable.

Store-only source coverage is 0.53% of metadata starts. It is not added
to the previous shared-dispatch metric until an integrated full-image build
and reconciliation. Ordered 1074, full-game link and gameplay were not run.
