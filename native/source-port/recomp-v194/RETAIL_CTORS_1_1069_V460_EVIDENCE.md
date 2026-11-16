# V460 — consecutive native returns 1–1069

The private hash-pinned Bloodborne 1.09 owner probe passed ordered startup through 1069 on Linux x86-64. Compared with 700, it adds original bodies 701, 954 and 1018 and 366 exact-pattern registrations. The replay asserts consecutive ordinal returns in a single process.

701 preserves object identity: it reuses the existing object from 243 as parent of the object created at 506. Its registry path exercises six relocation-verified getters; checks cover 38 keys and 152 sorted value/owner pairs. 954 and 1018 initialize two distinct native mutexes and register original cleanup callbacks. Post-prefix checks exercise the warm guard without duplicate registration, destroy both mutexes through those callbacks in reverse order, and verify arena reuse. The registered 615 destructor remains unsupported and is not invoked.

Passed 100 fresh ordered processes each with optimized GCC and Clang, and 10 with Clang ASan/UBSan on the C harness only. A separate Clang run passed the isolated batch of 12,045 registrations twice; it is not an ordered extension. The owner executable is read offline only; the run directory contains only the host executable and no PS4 executable, loader, interpreter or JIT. No proprietary input or derived outputs are committed.

1070 is outside the verified prefix. No game main, title screen, gameplay or Windows/macOS retail execution established.
