# New source-port donor verification: Win64 game recompilers beyond bbport (2026-10-31)

**Scope:** direct review of public repositories. None of the source evidence below is a user's actual Windows gameplay test, nor proof of the final requested game booting **without original PS4 ELF-derived code, PS4 import compatibility services or command-stream conversion**.

## [Astrr00/BloodbornePC](https://github.com/Astrr00/BloodbornePC)

This is a substantive **different** static-game-recompilation approach from the Wine-like `bbport`. The public `README.md`, `docs/ARCHITECTURE.md` and `docs/ROADMAP.md` claim a user-owned `eboot.bin` is compiled into C++ and linked by **MSVC** into a Windows `bbgame.exe`. The maintained CMake has `bbrecomp`, generated source shards, `bbrt`, `bbhle`, `bbgcn`, SDL3 and native launcher, tests that take synthetic guest instructions through *real* source generation to compiled code, and source/fuzz/differential test harnesses.

- Claims a Windows build of **176,896 recovered game functions**, generated into about **89 C++ shards**, linked to a large `bbgame.exe`, and differential checks against real CPU execution. This is a **developer-reported** source/build result, not independently reproduced by us.
- A user-owned PS4 executable is still required: public usage explicitly says `bbgame.exe <eboot.bin>`, while its runtime processes ELF segments and relocations and implements PS4 system calls (HLE) and GNM/GCN GPU translation. It is **closer to the CPU side** of the requested source port but **does not yet fulfill the no-PS4-executable/runtime-at-launch goal**.
- The public README's strongest gameplay evidence is for **Bloodborne v1.00**, with scripted combat aids and teleportation; **v1.09** evidence is only part of the initial areas / Hunter's Nightmare. Claims of a completed real all-boss playthrough or compatible Yharnam Together must **not** be inferred.
- Original `bbrecomp` code and `src/recomp/emitter.cpp` are worth comparing with the Mac-oriented `bloodborne-native/bloodborne-recomp` generator, especially **Win64 MSVC ABI**, native object/debug formats, function tables, TLS and exception handling. Its GPL-3.0-or-later source needs reviewed attribution if reused, not a wholesale transplant into an incompatible project license.

**High priority intake:** test its public *synthetic* generator-to-compiled-code test harness on a pinned GitHub Actions commit; audit actual generated library/export and PE/game runtime requirements; then compare any verified Win64 code-generation advantage against our V187/V188 LLVM COFF modules. Do not claim its `bbgame.exe` could simply replace our YT client, or that its 1.09 game boots as a completed Windows release.

## [NielsL92/bloodborne-pc-port](https://github.com/NielsL92/bloodborne-pc-port)

An independent **Remill/LLVM differential-recompilation experiment**, not a playable Bloodborne port. Public docs claim **11 real Remill root contracts**, 13,584 full-state cases, and an older 19-function x64 recompilation proof with 205,048 scalar comparisons. A later native-startup checkpoint reports **constructors 0–1080 / 18,444** before an unresolved execution frontier, with no full native gameplay. Its README explicitly marks the work unplayable. Use **verification methods**, pointer/TLS/exception coverage and mutation tests as research. Do not substitute its reported counts for Paleblood's independently verified readable C++ or bloodborne-recomp's automatically lowered instruction coverage.

## Consequence for the Windows roadmap

1. **V188 (this Draft):** prove clang-cl -> x64 COFF -> `lld-link` PE DLL with explicit `bb_recomp_init` export and actual Windows load/callback test; synthetic only.
2. Compare **two genuine public game recompiler approaches**, not only their marketing labels:
   - Mac ARM64 `bloodborne-native/bloodborne-recomp`: 240,978 functions run with generated C library on a compatibility host; high coverage but Windows builder and independent Win32 runtime open.
   - `Astrr00/BloodbornePC`: MSVC Windows C++ game shards and a real reported Windows `bbgame.exe`; still user PS4 ELF at launch and HLE/graphics translation, strongest reported run on 1.00.
3. Add **source-exact Windows code-generation test** derived from whichever generator has independently reproducible synthetic or user-private game-function tests. Keep source/derived game bytes private. Validate ABI, SSE/AVX semantics, exceptions, atomics, memory/TLS and calling conventions with repeated differential tests.
4. Replace remaining PS4 guest API/kernel/graphics runtime dependencies with genuine Windows-native engine services and a renderer at the Dantelion/GX boundary, using `bbhost`, `LanternEngine`, DS3 PC interfaces and Paleblood's named source as references.
5. Connect the genuinely Windows-native game core to the Yharnam Together server, five-player roles and measured authenticated Direct P2P.

**Evidence gate:** compiling a Windows PE wrapper, generated game C++ DLL or even an early-game `bbgame.exe` is NOT enough. Final startup must not load the original PS4 ELF or a converted guest flat image, and must not rely on PS4 kernel imports, GNM command processing, or a PS4 game compatibility runtime at play time.

All donor facts are **source-derived**, and no proprietary game bytes or derivative generated C are committed. This file is research, not a source-copy grant or production claim.
