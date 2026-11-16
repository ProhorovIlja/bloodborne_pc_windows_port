# V456 — consecutive native startup returns 1–176

The hash-pinned private Bloodborne 1.09 Linux x86-64 probe returned from corrected constructors 1–176 in order, without gaps in one process. Beyond V455 this includes 13 reassembled original constructor bodies and 39 exact-pattern native registrations. The harness checks the return ordinal after every callback.

The new bodies exercise reuse of the existing parent singletons, another original parent getter, registry insertions and six additional attachments, including two children for one owner and an auxiliary key publication. Assertions cover 22 registry keys with explicit/computed length, a missing key, 88 sorted value/owner pairs, all eight attachment mutex identities, descriptor links and balanced allocator locks. Post-prefix checks cover reference vector growth and arena reuse. Descriptor callbacks and unsupported branches trap; the cleanup assertions are probe cleanup, not retail teardown.

Verified 100 fresh ordered processes each with optimized Clang and GCC, and 10 with Clang ASan/UBSan on the C harness (not the assembly). The isolated 12,045 registration batch also passed twice in a separate run; this does not extend the prefix. The owner image is read offline at build time only. Runtime directory contains the host executable only, without console executable, PS4 loader, interpreter or JIT. No original bytes, private offsets or derived binaries are published here.

The next untested constructor is 177. Game main, title screen, gameplay and Windows/macOS retail execution are not established.
