# V492 — read/write AOT integration and regression repair

V491 Linux and Windows failed the store fixture with return code 6.
The negative-displacement test encoded RDI (ModRM BF), but expected RSI.
It now encodes RSI (B7), with an explicit decoder assertion for the signed
displacement, size and source. This was a fixture error, not evidence of
incorrect retail store semantics.

The V492 build emits four non-overlapping families in one inventory:
register, load, arithmetic, and store. Store permission uses a separate
mutable span. A recognized but rejected write never falls through to
another family. Successful stores preserve RAX and arithmetic flags.
CI checks all four routes, read/write denial, miss, and unchanged data
on rejection. The generated binaries and image remain private.

The unified retail build and ordered startup were not rerun here. Do not
add the V491 standalone store count to the last confirmed common total
until the real image is emitted, compiled, and run through V492.
