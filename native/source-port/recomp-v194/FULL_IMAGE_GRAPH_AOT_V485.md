# V485 — a linked subset with checked direct transfers

Reuses both V483/V484 decoders and emits one C unit and one exact-ID entry
table. Byte windows stop at the next metadata start. Single JMP and
CALL/RET wrappers close only over known starts with a terminal leaf and
at most eight transfers. Cycles, interior entries, unresolved targets and
over-depth chains never enter the table. The generated code uses direct
native C calls for the resolved edges; no runtime branch decoding.

Owner-local CUSA03173 1.09: 18,000 previous leaves plus 439 near JMP
wrappers. The other 7,505 wrapper-shaped starts did not close under
these rules. The accepted set includes one constructor entry (18374),
tested alone, not in ordered startup. CALL/RET was exercised with a
synthetic fixture, not seen in the accepted retail set.

On Linux x86-64, compiled static GCC and Clang executables ran in a chroot
without game inputs. Each matched 1,180,096 RAX/defined-arithmetic-flag
results at 64 inputs per ID. The separate reference used original leaf
instructions and the original direct JMP graph with branch displacements
adjusted to the reference layout. RCX/RDX/RSI were held at zero, RAX/RDI
and arithmetic flags varied. This checks observable leaf results, not
guest stack traffic, unwind, or nonlocal control flow. Only register
leaves and wrappers unable to observe the guest return stack are in scope.
No new ordered startup, full V204 link, or game boot claimed.

N64Recomp independently demonstrates direct native calls and tail-call
lowering. Its MIPS/ROM runtime is not used. All private outputs stay local.
