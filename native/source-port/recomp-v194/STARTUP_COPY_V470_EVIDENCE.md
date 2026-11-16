# V470: startup constant-copy family
Owner-local CUSA03173 scan: 1,232 exact leaves of AVX RIP-relative aligned
16-byte load/store pairs followed by ret: 3 single-pair, 1,228 triple-pair
and 1 quadruple-pair callback. There are 3,691 distinct source blocks and
3,691 distinct writable destination blocks. Sources are file-backed, their
ranges do not overlap any examined leaf instructions, and no source or
destination block intersects a relocation. Seven leaves are before 1074.

Reference: execute only opcode-verified leaves and record destination bytes
and all 32 bytes of YMM0. Candidate: use a deduplicated data pool with offsets
and model YMM0 in host memory, clearing its upper 128 bits. Test at three
initial destination patterns, in ordinal order within this family. GCC and
Clang static binaries each matched all 3,696 lines inside a Linux chroot
with no game executable, guest libraries, or runtime data files. Synthetic
tests also pass with ASan/UBSan. No game-derived inputs or traces committed.

V469 and V470 together account for 13,277 of 18,444 startup entries in
isolated family replays. Neither is the real ordered constructor run.
Ordinal 1074 is not in this new family and remains unverified. The helper
does not implement arbitrary AVX or validate call ABI; caller owns the rest
of CPU state. It uses no AVX intrinsics and is not a general replacement
for the original RX segment.

Independent references: Astrr00/BloodbornePC bbdiff (original-vs-recompiled
differential checks), bloodborne-native/bloodborne-recomp (instruction
fuzzing and trace replay), and NielsL92/bloodborne-pc-port (full-state tests).
Use their approaches for validation; do not import a runtime fallback.
