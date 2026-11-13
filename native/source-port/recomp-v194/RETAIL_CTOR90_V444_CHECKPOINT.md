# V444: corrected constructor 90 enters native pool initialization

The private CUSA03173 rebuild adds five native bodies or bounded prefixes: constructor 90, its pool getter prefix, reader/writer lock initialization and ready method, and the pool initializer. The resulting probe covers 3,818 input bytes across 13 such regions, separately from the 87 exact-pattern registration bodies. Local relocations validate the lock and allocation slots; the reader/writer lock import NID matches scePthreadRwlockInit.

The probe runs 1–89, then enters 90 on the same CPU process with their state retained. It executes the original pool setup against a 1 MiB aligned backing region, and the host checks pool publication, guard and mutex initialization, reader/writer lock behavior, and the requested first allocation (40 bytes, 8-byte alignment). It terminates at the virtual allocation before returning any pointer. The launcher distinguishes this exact checkpoint marker and exit status from a return or arbitrary crash. The original allocator method was identified from the vtable relocation but is not implemented in the probe. Other unbound paths abort.

GCC and Clang optimized builds, the Clang ASan/UBSan host shim build, and 100 fresh Clang processes per mode passed. The separate baseline mode rechecks returns and repeat behavior for 1–89; the checkpoint mode does not count constructor 90 as returned. No EBOOT or PS4 ELF is loaded at runtime; no JIT/interpreter fallback. Sanitizers do not instrument reassembled bodies.

A static scan of all 18,444 corrected callbacks found 12,045 matching the registration instruction pattern and 49 matching constructor 90's masked entry prefix. These are candidates for batching, not closure, coverage, or a claim of matching semantics. Resolve dependencies and preserve order and cell aliases before claiming returns.

Next: translate the resolved virtual allocation method and its pool free-list routines, then validate the allocated node and constructor return. This is not a game boot, playable build, or Windows/macOS result. No proprietary bytes, addresses, generated assembly, or executable are published.
