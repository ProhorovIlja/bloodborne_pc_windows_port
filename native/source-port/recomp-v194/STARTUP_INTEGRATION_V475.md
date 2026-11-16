# V475: prepared writable image plus native startup projection

The V473 replay can now initialize its actual writable state via V474, in
the same process before dispatching any constructor. The input is trusted
build-linked data and patch rows. The default V473 fixture still works.
Invalid plans or dirty relocation cells stop the replay before its first
trace line. The new fixture covers a pre-set guard, file-backed and
zero-fill relocations, writes shared by all three families, and a rejected
relocation overlapping a nonzero initializer.

Private Linux x86-64 check: linked the normalized writable template,
235,000 patch rows, a pool of 3,757 verified 16-byte source blocks, and the
same 13,300 ordered-with-gaps V473 leaves into static GCC/Clang builds.
Each ran from a chroot without original game files, runtime libraries, or
external data packs. Each matched all 13,300 step traces; separate
diagnostic builds compared all 6,254,836 final writable bytes against the
reference after normalizing the original leaf's host-address stores.
The reference started with original writable bytes and applied independent
expected patch values before executing only the recognized leaves.
3,522 symbol relocations still use synthetic bindings. No private inputs
or outputs were committed. ASan/UBSan also passed the synthetic fixture
and its rejection case. TLS is not exercised by this projection.

This integration does not add constructor coverage, attest ordinal 1074,
or run game main. V461 remains the contiguous 1–1073 result; 5,144
entries are omitted by the projection. LanternEngine is a useful
comparison for native host services and Vulkan, not for an AOT-only
replacement: it prepares and reuses the original game's executable code.
