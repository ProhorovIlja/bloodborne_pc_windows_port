# V486 — batch lowering of bounded memory getters

Scanned the same owner-local CUSA03173 1.09 metadata starts as V485.
4,578 exact RDI-relative memory getters, disjoint from the 18,439 V485
entries; none are legacy constructors. The generated unit contains an
exact-ID table and one native load path. It preserves MOV's 32-bit
zero-extension and MOVSX/MOVSXD source and destination widths, including
unaligned bytewise little-endian loads. The caller supplies a bounded
guest data region; no arbitrary host pointer conversion or guest
fallback occurs. This is not a general MMU or proof of callsite provenance.

The private Linux x86-64 oracle executed extracted original getters;
GCC and Clang static candidates each matched 292,992 RAX outputs
(64 data/offset cases per ID). Each also rejected 9,156 out-of-region
accesses with the output unchanged. Both candidate executables ran in
a chroot containing only the host executables. Private data and generated
code were not committed. V485+V486 give 23,017 separate tested IDs, not
a unified runtime or a full-game AOT link. No new ordered boot evidence.
