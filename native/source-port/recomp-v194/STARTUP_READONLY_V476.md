# V476: bounded read-only operand pool
The owner-local CUSA03173 1.09 test selected 3,757 previously verified
vector constants plus five strings referenced by the body of constructor
1074: four byte strings (including a UTF-8 diagnostic) and one UTF-16LE
string. The latter must not be sized with byte strlen. RIP-relative
operands and terminators were checked against the original. The packer
rejects intersections with supplied decoded-code ranges or relocation
slots. It does not infer that every unindexed byte is data.

The private pool contains 60,370 bytes in 698 contiguous ranges.
On Linux GCC and Clang, every one of 3,762 requested reads matched the
original byte for byte, all four byte-string lengths matched, and each
of the 697 holes between ranges rejected a read, per compiler. The C
reader has no file loader or guest call mechanism. The owner-local test
driver used the ELF as the reference and passed only the pool and
index to the C reader; no game bytes were added to GitHub. Synthetic
tests also reject out-of-bounds and overlapping entries and passed
Clang ASan/UBSan. This reader is not yet wired into V475 or the
contiguous startup harness.

External comparison: PS4Recomp demonstrates standalone Apple Silicon
AOT packaging but does not establish strict working Bloodborne.
bloodborne-runtime prepares the original executable in memory; its
startup model is not used here. No new ordered return is claimed.
