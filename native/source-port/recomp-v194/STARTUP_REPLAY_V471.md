# V471: combined sparse projection and strict negative control

Combines V469 and V470 as one host executable with two compile-time data
tables. Validate both complete tables before mutation; reject ordinal
collisions, bad order, invalid indices, and copy offsets outside the declared
pool/state. Merge in original ordinal order with two cursors; keep shared
guard state. Projection explicitly allows gaps; strict mode stops at the
first missing ordinal and never asserts startup completion or invokes a guest
target. The strict mode is a test of missing coverage, not the V461 harness.

Private Linux x86-64: confirmed disjoint original write spans across the two
families before using independent buffers. Compared one combined 13,277-line
trace per compiler to the merged V469 and zero-state V470 reference traces.
GCC and Clang static binaries each matched line for line in a chroot holding
only the two native executables. Strict mode on these tables stops at ordinal
1 with no trace output, since this isolated plan is not the V461 plan. The
synthetic fixture mixes both routes at 1,2,4; strict stops at 3 before 4.
Wrong copy span and cross-family collision fail before any trace output.
Public fixture also passed Clang ASan/UBSan. No private header or trace
committed. No added callback coverage or full 1074 return claimed.

Donor check: rev.ng's iterative indirect-edge discovery can serve as an
offline independent comparator, not a source of runtime fallback. Astrr00's
documented bbgame invocation still takes the original eboot, and
bloodborne-runtime still loads the original executable. Neither replaces
strict runtime isolation. The two-family replay cannot validate side effects
of any omitted callbacks, including initialization of shared registry state.
