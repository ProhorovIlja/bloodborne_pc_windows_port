# V459 — consecutive native returns 1–700

The private hash-pinned CUSA03173 1.09 Linux x86-64 probe checks every constructor return through 700 in one process. The delta is original bodies 506, 615 and 640 plus 192 exact-pattern registrations.

506 uses the original arena flags, publishes its singleton, registers through six relocation-verified virtual getters, and links to the object produced by the original parent getter. Probe checks both guards, allocator identity, parent and key/label links, 37 keys in both lookup modes, and 148 sorted value/owner pairs. 615 runs its original base and flags helpers, checks bit masks and selective zeroing of seeded fields, and registers a destructor. That destructor is a fail-stop binding and is not executed. 640 initializes a vector against the existing default heap, registers its original cleanup and exercises the empty branch. Nonempty cleanup and whole-game shutdown are not established.

Passed 100 fresh ordered runs each with optimized Clang and GCC, and 10 with Clang ASan/UBSan on the C harness only. The separate 12,045 exact-pattern batch passed twice and is not an ordered replay. The original image is read offline only. At runtime the isolated directory contains only the host executable, no PS4 ELF/loader, interpreter or JIT. No original bytes, private addresses or generated outputs are published here.

701 is the next unverified constructor. Game main, gameplay and Windows/macOS retail execution remain unverified.
