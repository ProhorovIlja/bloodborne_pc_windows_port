# V468: data-only startup leaf replay

The owner-local 1.09 CUSA03173 pack contains 390 verified V463 callbacks
at their exact ordinals in 1074–1500 (14,052 bytes, no guest instructions).
There are 390 distinct callback entry points, but only three distinct
object/guard pairs, each shared by 130 callbacks. The builder verified the
opcode pattern, adjacent writable object/guard and executable-relative
vtable slot. The isolated reference mapped only the recognized original
leaves; on shared initial state, exactly three callbacks wrote to memory.
The other 387 observed guards already set by earlier callbacks.

The V468 candidate loaded the pack, externally pinned digest and native
V463 library inside a Linux chroot with no original ELF, PS4 libraries or
game directory. GCC and Clang builds each passed 780 invocations (390
callbacks plus immediate reentry), preserving aliasing, guards and canaries.
No guest target is dereferenced or called. The packet stores guest IDs and
16 bytes of initial object/guard state per row, not a replacement executable.
Do not publish owner-local packs.

For a private run: pass the pack, pinned digest file and trusted compiled
V463 shared library to replay_startup_v468.py. The offline caller supplies
rows validated for its exact dump. The digest identifies the expected
packet; it does not certify provenance or authenticate a host library.
The test skips all non-V463 constructors and does not establish their
effects on the three objects. This does not extend the contiguous ordered
startup prefix, pass 1074, or reach gameplay.

Comparators: bbport's flat image still includes executable guest code and
console library code; do not use it as a data pack. droogie/bbhost and
Astrr00 still document original eboot input, and bloodborne-native's
runtime retains translated guest code. Unleashed Recompiled shows a useful
installer/runtime separation, not a reusable PS4 loader.
