# V473: three-family replay with shared writable state

The V463, V470, and V472 implementations now run in one process and one
normalized writable address space. The private plan is sparse: it contains
13,300 verified leaves (12,045 guard, 1,232 copy, 23 mixed stores) and omits
5,144 entries. The reference loaded only those leaves and their data into an
isolated mapping. Initial state consists of original bytes for the touched
spans and zeroes in the gaps; it is not the state after omitted callbacks.
The three families had no pairwise write overlap in this private plan. The
public fixture deliberately overlaps all three and verifies that a copy
clears a previously set guard so the last leaf initializes it again.

On Linux x86-64, GCC and Clang static candidates ran in a chroot holding only
the two candidate executables. Each matched 13,300 reference lines and the
final diagnostic fingerprint across the whole 2,829,488-byte shared span.
Guest pointer values were normalized; guard status was inferred from the
reference guard before execution. This is not a full CPU-state comparison.
Clang ASan/UBSan passed the overlapping fixture and rejected an out-of-bounds
plan before output. No original bytes or game-derived files are committed.

Separate 1074 audit: beyond the two direct-root slot-0x20 sites, two reached
helpers have the same cold singleton-cache pattern and test the same bit on
the returned structure. Both use the cached subobject at +0x458; the cold
constructor writes its vtable before publication. Route selection for the
warm object, the helper's slot-0x58 and slot-0x70 calls, and ordered execution
with the previous startup state remain unresolved. V473 does not extend the
contiguous 1–1073 evidence or claim game startup.
