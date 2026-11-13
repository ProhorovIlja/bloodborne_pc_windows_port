# V414: ordered retail startup through constructor 92

The private Linux AMD64 harness runs constructors 1–92 in order on a
single retained VM. Constructor 89 is a non-leaf initializer, not another
shared-guard skip. Its path required real relocation-backed virtual call
targets, more generated native callees, reused recursive mutex state, an
exclusive rwlock, and a write at a negative offset from the logical TCB.
Constructors 90–92 then checked or published their expected guarded objects.

The private run checked return RIP/RSP and the saved return word, a TLS
write within the 1,872-byte zero-fill block, the rwlock token, and balanced
mutex and rwlock state. Optimized Clang, optimized GCC and Clang ASan/UBSan
passed. The test working directory contained no EBOOT. Its 123 registered
functions use selected privately prepared data and relocation slots; it
does not run the real process entrypoint, use a fallback interpreter or
boot the game. Unknown calls and fallback callbacks stop the test.

Public code adds a restricted init/write/unlock rwlock adapter and bounded
zero-fill TLS setup. These are startup pieces, not a full pthread or dynamic
TLS implementation. The private harness used the same bounded operations
and audited private callsites. Public CI tests invented slots only.
Private generated source and addresses are not part of this PR.

Next boundary: ordinal 93 is another non-leaf constructor. Start from the
same retained VM and verify its callee and relocation closure before
counting it as executed. Do not promote this result to boot, gameplay,
rendering, performance, network or launcher readiness.
