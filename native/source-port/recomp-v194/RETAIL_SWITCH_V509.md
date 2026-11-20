# V509 — first retail switch route replay

On the pinned private CUSA03173 1.09 image, an LLVM direct-edge walk from ELF entry and DT_INIT reached one of the 161 V508 guards. Adding the first 1074 and then all 18444 constructor roots found no additional V508 guards by direct edges. Indirect transfers were not resolved. This is static reachability, not a startup trace. GNU objdump independently agreed with the guard, table and target instruction boundaries.

The selected table has 23 entries, 7 distinct case targets. The isolated original dispatch used its original table and synthetic return stubs in place of the case/default bodies. Both Clang and GCC emitted selectors matched its destination on 259 unsigned indices each. Native selector reruns were performed after unmapping the original dispatch and dropping the image bytes. This tests target selection, not the original block bodies, guest state or full-game boot. No game code, offsets or generated private outputs included.

The existing bloodborne-recomp bbrecomp.c and Android Rebuild Tool lifter.cpp already recover broader families and preserve local block structure. Prefer comparing their recovered blocks to the exact-image result rather than enlarging a local byte pattern scanner into a new general lifter.
