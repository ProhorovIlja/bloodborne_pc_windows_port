# V482 — classify indirect edges and PLT import consumers

Owner-local CUSA03173 1.09, LLVM 19: repeated the V481 accepted-instruction
walk; examined exact RIP-relative FF /2 and /4 encodings with SCE RELA and
scoped symbol metadata. A direct consumer is attributed to a PLT thunk only
after matching its jump slot, push ordinal, resolver signature and original
GOT backlink. An independent reverse check from the initial GOT values
validated all 661 PLT entries against their relocation order and one common
resolver. No addresses, game bytes or derived symbol lists are published.

Private inventory: 101,341 direct call sites (601 scoped identities) and
9,735 direct jump sites (126 scoped identities) entered recognized PLT
thunks. These are consumers, not distinct functions or implementations.
The indirect-site partition of the same walk was:

| Kind | Scoped import | Relative RX candidate | No relocation | Other operand |
| --- | ---: | ---: | ---: | ---: |
| Call | 0 | 1,681 | 4 | 154,495 |
| Jump | 641 | 0 | 0 | 15,101 |

The 641 recognized indirect jump sites identify a scoped import, not a
native binding. Relative RX entries are candidates, not callable by
default; register/SIB/segment and dynamic table cases stay unresolved.
The analysis neither follows new targets nor modifies generated code.
Native generation, strict link, contiguous 1074 and gameplay are not
claimed. Runtime must use exact scoped host bindings and refuse misses.
