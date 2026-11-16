# V479: correct the 1074 mutex branch boundary

The bounded disassembly of the CUSA03173 image separates two adjacent
functions that a previous wider window conflated. The direct target in
1074 is a complete four-byte leaf: load the initialization byte at
receiver+16 into AL, then return. It neither locks nor calls an import.
The nearby longer wrapper really calls scePthreadMutexLock with
receiver+8, as confirmed by the PLT/GOT relocation and scoped symbol.
It is not the direct target. Do not add a lock or a success stub on
the basis of that adjacency; this is not a complete indirect call graph.

There are two direct probe sites in 1074 and two in the helper reached
from its second registry publication. All four pair the probe with
the same conditional attribute-init/type-2/mutex-init/attr-destroy wrapper.
The mutex/once state is shared with 1070, which has the same two direct
probe sites of its own and sets the same outer once byte when it takes
the initialization block. The three intervening leaf constructors
1071–1073 have disjoint direct write spans. Therefore check the actual
once byte on entry to 1074 before treating cold mutex initialization
as the blocker. This does not prove the byte stayed set across all
other calls inside 1070, or certify the live 1074 receiver. The two
registry cache cells written by 1070 are distinct from the cache cell
accessed by 1074; a warm shared mutex does not imply a warm 1074 registry.

The native probe uses the V478 data adapter and checks site and receiver
identity. It preserves the upper 56 bits of RAX and leaves all memory
unchanged. Offline differential (Linux x86-64): exact original leaf on
the reference side, 256 byte values x 8 RAX seeds x 4 synthetic route IDs
x 2 compilers = 16,384 comparisons. Both static candidates passed in a
chroot without game inputs; Clang ASan/UBSan and negative cases passed.
No retail bytes, private addresses or generated binary were committed.
No complete 1074 return or additional contiguous coverage is claimed.
