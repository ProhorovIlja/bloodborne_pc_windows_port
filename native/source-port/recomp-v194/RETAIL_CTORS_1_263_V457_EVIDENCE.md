# V457: ordered native startup returns 1–263

A private hash-pinned CUSA03173 1.09 Linux x86-64 probe returned consecutively from constructors 1–263 in one host process. The delta from 176 is 15 reassembled original constructor bodies and 72 verified exact-pattern native registrations. Each return advances the checked ordinal by exactly one.

The added registry paths cover shared parent objects created before their own registration, multi-child attachment vectors (including a parent with eleven children), and descriptor/auxiliary data publication. Assertions cover 36 keys in both lookup modes, 144 sorted value/owner pairs, 27 attachment/mutex identities, and arena release and reuse. Unsupported descriptor callbacks and diagnostic branches still trap.

Constructors 256 and 260 now take the original heap getter and flags path, initialize their vectors using the already-published default heap, and register the same original cleanup routine through a bounded host binding. The offline build verifies the imported atexit NID and relevant vtable relocation. The post-prefix check confirms the vector and configuration state and invokes both original empty-vector callbacks in reverse registration order. Nonempty vector cleanup and full game teardown are not exercised.

Passed 100 fresh ordered processes each with optimized GCC and Clang, and 10 with Clang ASan/UBSan on the C harness (not the generated assembly). The isolated 12,045 registration-pattern batch passed twice separately and does not extend the prefix. At runtime the isolated directory contains only the native host executable: no EBOOT, console executable, PS4 loader, interpreter or JIT. Game input is read only offline. No original bytes, offsets or binaries are published here.

Constructor 264 is the next unsupported entry. Game main, title screen, gameplay and retail execution on Windows/macOS are not established.
