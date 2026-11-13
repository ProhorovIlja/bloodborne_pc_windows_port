# V445: native allocator and vector reserve within constructor 90

After corrected constructors 1–89 returned, the same Linux x86-64 process entered 90 and executed the reassembled allocator wrapper, aligned and ordinary allocation cores, and vector reserve path. The first 40-byte node was published, and the original reserve path allocated 768 bytes and initialized the empty vector's begin, end and capacity pointers. The probe intentionally stops before the next pool-getter setup call. Constructor 90 did not return.

Host-side tests then exercised the reassembled free core with scoped pthread lock bindings. Nine simultaneous allocations at alignments from 8 to 4096 were bounded and disjoint, with payload integrity checked. Non-power-of-two alignment and a request larger than the arena returned null. 512 allocation/free cycles succeeded and a 960 KiB allocation fit after freeing test blocks. The probe verified 1048 balanced lock/unlock pairs and released host resources.

Clang and GCC optimized builds and Clang ASan/UBSan host shim passed. Both baseline and checkpoint modes passed 100 separate Clang processes each. The 17 translated bodies or bounded prefixes cover 5,860 input bytes, plus 87 separately pattern-translated registration routines. The run directory has only the native probe, no PS4 EBOOT/ELF, JIT or interpreter. The assembly is not sanitizer-instrumented. AVX, BMI1 and LZCNT are checked at startup. Unsupported guest TLS path traps. No public game data or private bindings.

Next: translate the pool getter's remaining setup call, finish the registry path in constructor 90 and verify its return. This checkpoint is not game boot or cross-platform retail verification.
