# V451 constructor 90 registry success-path probes

The private 1.09 x86-64 input was available again. Independently inspected the actual entry wrapper and initializer loop: the forward table range is empty, the backward loop reads before decrementing, and its relocation-resolved order has 18,444 distinct non-null targets. This is a static count, not a count of successful returns.

Two separately linked Linux x86-64 native probes exercised original instruction regions reached beyond the V446 string-length checkpoint:

* Primary vector: initial reserve of 512 records, unsigned upper-bound by key length, stable insertion for equal lengths, 32-byte row writes, shifts and 1.5x growth. Across eight runs of 4,096 insertions, compared all rows to an independent reference after each insertion. Covered equal, ascending, descending, high unsigned and mixed lengths; allocation/release counts balanced.
* Secondary vector: initial reserve, four virtual getter dispatches with fixture targets, append of four value/object pairs, and execution of the original growth helper. Checked all 16,384 pairs produced from 4,096 fixture objects and balanced allocator ownership. This probe stops before the subsequent sort call.

Both probes passed GCC and Clang optimized and Clang ASan/UBSan host-harness builds. The assembly slices themselves are not sanitizer-instrumented. Runtime directories contained only native host probe executables; original bytes were read only by the offline build. These are bounded assembly slices with synthetic ABI frames, host malloc/free adapters, and traps in unsupported diagnostic branches. No full image was mapped and no PS4 loader, interpreter or JIT ran. No addresses, original bytes or binaries are published.

Not yet covered: connecting the primary and secondary segments using the original singleton getter and virtual targets, the subsequent sort, diagnostic/TLS failure handling, the caller's remaining work and a checked return from constructor 90 in the same process after constructors 1–89. This does not prove whole-game boot, nor Windows or macOS retail execution.
