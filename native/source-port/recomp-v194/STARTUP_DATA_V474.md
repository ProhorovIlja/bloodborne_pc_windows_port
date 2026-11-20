# V474: writable image and TLS templates, no guest ELF at runtime

Offline preparation copies only the writable LOAD's file data, zeroes
relocation cells, and describes its zero-fill tail. TLS is separate: the
owner's CUSA03173 ELF has a 1,872-byte TLS block, 16-byte alignment and no
file-backed initializer bytes. This does not establish FS/GS, TCB, canary,
alignment of caller-owned buffers, or multithreaded ABI behavior.

The native C initializer accepts trusted build-supplied bytes and resolved
guest values, verifies all sorted patch spans and zeroed cells before touching
the destination, then copies, zero-fills and patches without reading any file
or interpreting a guest executable. No RX segment, original game data, or
generated files are committed. Read-only constants outside the writable LOAD
remain a separate problem; callable guest IDs still require native dispatch.
This is not yet wired to the V461 ordered harness.

Private Linux differential: GCC and Clang, two base addresses each, all
235,000 relocation cells and the entire 6,254,836-byte writable span compared
byte for byte against a reference built from the original writable bytes,
with outside canaries. Of the relocations, 231,478 are relative; the 3,522
symbol values were synthetic, not implemented retail imports. The reference
driver had access to the original; the candidate initializer was called only
with prepared bytes and patch rows. Public fixture also verifies rejection
before writes and independent TLS block initialization. No new constructor
return or gameplay verified.

Donor check: ducvd89/Bloodborne-android-rebuild-tool is an independent LLVM
AArch64 comparator for linked-image discovery, switch-table resolution and
FEX differential checks, not an ELF-free runtime donor. Its README places AOT
output next to eboot.bin; its plan uses a linked image including libc.prx and
libSceFios2.prx and describes an interpreter for misses.
