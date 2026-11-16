# V477: integrate the immutable operand view into prepared replay

The prepared replay now accepts vector operands as normalized guest
addresses in its optional V477 mode. It resolves every vector operand and
verifies bounded byte and UTF-16LE string lengths before initializing
writable state or printing the first trace. The existing offset-based
fixtures remain valid. Each call stages at most 96 bytes on the stack;
packed offsets need not be multiples of 16 and guest IDs are not host
pointers. Wide lengths count 16-bit code units, not Unicode characters.

Owner-local Linux x86-64: the 60,370-byte immutable pool, five string
requests, writable template and 235,000 patch rows were linked into static
GCC and Clang builds. Both ran in a chroot containing only the candidates.
Both matched 13,300 per-step lines and the final fingerprint against the
V475 reference; separate diagnostic variants matched all 6,254,836 final
writable bytes. The public ASan/UBSan fixture passed. A missing vector
range and incorrect wide-string length were rejected before output. No
game bytes or private plans were added to Git.

This is still a sparse projection with 5,144 omissions. It validates
resource access for five strings referenced by 1074, not execution of
1074 or its callees. Symbol bindings remain synthetic. The contiguous
retail evidence remains V461 (1–1073).

External cross-check: Astrr00's bbdiff is a useful model for offline
differential testing. bloodborne-recomp documents an interpreter for
unrecompiled code on x86-64. rev.ng documents iterative offline discovery
from direct edges and candidate data pointers; guessed data pointers
are not trusted dispatch routes. No donor runtime was introduced.
