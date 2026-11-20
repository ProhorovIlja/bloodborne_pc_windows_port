# V472: mixed vector and scalar startup stores

Owner-local CUSA03173 scan of the 5,167 entries outside V469/V470 found
23 more complete leaves in four opcode forms: 18 with three aligned vector
copies and a 16-bit scalar store, two with three copies and a 32-bit store,
two with one copy through RAX, and one with five copies and a scalar store.
The first is at ordinal 2276. Decoder validates mapped spans, alignment
and overlapping relocations. Instructions not in the exact forms stay
unclassified. No executable or private constants are committed.

Linux x86-64: 138 comparisons across 23 leaves, three initial fills and
GCC/Clang. Both static host builds independently ran in a chroot containing
only the two candidate binaries. Full checked destination spans, canaries,
normalized RAX and all 32 bytes of YMM0 matched the original reference.
Synthetic decoder and native rejection fixtures and Clang ASan/UBSan passed.
Across V469/V470/V472, 13,300 distinct startup ordinals have isolated parity;
V472 is not wired into V471 and that sum is not an ordered run.

## Ordinal 1074 cross-check

Both root sret calls test the returned low byte against mask 0x20 and
branch around the diagnostic if that bit is set. The V464 cold-path leaf
returns 0x73, so both diagnostics are bypassed only when the verified
receiver/slot path is actually taken. That is a checkable trace predicate,
not license to delete the branches or assume a cached receiver. Rechecked
the five mutex imports by SCE JUMP_SLOT and scoped symbol identity. The
V413 backend is a recursive host mutex; existing V413/V416 bindings and
their memory adapter must still be exercised with live guest state.

Upstream comparison: bloodborne-recomp's split between per-instruction
and captured-call differential tests is relevant to validating full state.
Astrr00 builds an AOT bbgame but still starts it with the original eboot.
PS4Recomp is a separate ARM64 packaging and synchronization reference.
No donor code or runtime fallback added. Ordered 1–1073 evidence remains
the last contiguous result; no new full constructor return is claimed.
