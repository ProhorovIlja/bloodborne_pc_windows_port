# V518: Native startup entry boundary

Private 1.09 ELF entry replay: the seven calls were redirected to recording callbacks, a RIP-relative callback reference was relocated, and a test epilogue handled the deliberately returning exit hook. Neither actual initialization nor game main ran. The NID names were cross-checked with bloodborne-recomp's import inventory. Astrr00's bbdiff is a leaf-function differential harness; this test uses the same native-reference idea but intercepts the calls at the entry boundary.

The C boundary matched 256 original traces on each of GCC and Clang, including 32-bit argument and return patterns. A second process reproduced the 512 comparisons with the original dump directory mounted over by a read-only empty directory, using traces only and no guest instructions. Synthetic C tests also passed with Clang ASan/UBSan. This is not yet wired to real init/main or the full native dispatcher. No game bytes or retail offsets are committed.
