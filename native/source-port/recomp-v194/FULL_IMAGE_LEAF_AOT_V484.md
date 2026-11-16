# V484 — register leaves with partial-register and flag semantics

Private CUSA03173 1.09: 6,989 additional exact leaves from the same metadata
seed set, disjoint by guest ID from V483: 4,721 XOR-zero, 793 MOV AL
immediate, 1,475 LEA RDI. None are legacy constructor entries. Combined
V483/V484 isolated AOT count is 18,000. LEA computes a value and does not
access memory; MOV AL keeps the upper 56 bits. XOR defines CF, PF, ZF, SF
and OF; AF is architecturally undefined and is excluded from its validity
mask. Callers may not treat the placeholder AF bit as a defined result.

The generated C includes an exact-ID binary-search dispatcher that leaves
the output untouched on a miss and cannot jump to a guest address. This is
a leaf-only dispatcher, not permission to use an ID at every callsite. The
controller still owns caller state, guest RET and the stack. No runtime
decoder, executable image, or guest fallback is used by the candidate.

Each static Linux x86-64 candidate (GCC, Clang) matched 447,296 outputs
against a separate original-instruction reference, comparing RAX and all
architecturally defined arithmetic flags across 64 input cases per ID.
Candidates ran in a chroot with only the two host executables. Generated
code, private IDs and reference bytes are not committed. V204 full-image
generation, full-game dispatch/link, ordered 1074 and gameplay are not
claimed.
