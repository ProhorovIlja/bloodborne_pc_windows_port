# V488: straight-line AOT with explicit arithmetic flag semantics

New offline decoder/emitter recognizes up to eight operations followed by a
plain RET. Accepted register writes are limited to RAX/EAX; arithmetic flags
are explicit. It handles supported register/immediate ADD/SUB/CMP and
AND/OR/XOR/TEST, MOV, and selected LEA addressing forms without memory access.
Unrecognized prefixes, instructions, control flow and out-of-span bodies
are not emitted. AF is excluded for logical operations. The shared dispatcher
optionally routes these exact IDs; no runtime guest decoder is involved.

Owner-local CUSA03173 1.09 scan: 24 IDs outside the V487 set (20 single-op,
four two-op). None are constructors. GCC and Clang static Linux candidates
each matched all 1,536 RAX and defined-flag results against the original
sequences, with RCX/RDX/RSI zero in the retail reference. The candidates ran
in a chroot with only native binaries. These are isolated semantics tests,
not a full-game runtime, completeness or strict boot result. No retail code
or IDs are checked in. This does not advance the 1–1073 contiguous result.
