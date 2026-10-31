# V187: real Windows DLL ABI feasibility for static Bloodborne recompilation

This is an **independent, source-only experiment** for the final Windows game port.
It tests **the published `bloodborne-recomp` module ABI v4**, not any user's game.
The pin is `bloodborne-native/bloodborne-recomp@8f31ec7c41f252730c6325d52647046baef7549f`, public GPL-2.0-or-later source. All source files in this directory are hand-authored ABI probes with synthetic fake game functions.

## Actual technical result this is meant to prove

The library host can load a native Windows AMD64 **PE DLL** through `LoadLibraryA` and locate `bb_recomp_init` with the same RcApi / RcFunction *binary structure and exported name* as the upstream recompiler's version 4. Windows MSVC and Linux GCC compilers must both build and execute the same positive/negative tests. The test invokes one entirely synthetic compiled function via a host callback and rejects a deliberately invalid module. An upstream public header guard rejects interface drift, and detects whether the current upstream *build script* is still macOS-only.

### Explicit limitations, essential for an honest port

- **No real Bloodborne function was recompiled here.** The fixture's `struct BbCpu` includes only the actual upstream register-field prefix. The original header contains many more CPU/vector, JIT and trace fields. Complete ABI alignment must be proven against that public header and runtime; a matching `RcApi` declaration alone does not prove native game compatibility.
- The released upstream `build_library.py` currently emits `--target=arm64-apple-macos15`/`ld64.lld`/Mach-O `.dylib`. It is **not** currently a Windows game library builder. Building a real Windows DLL locally from a player's own decrypted eboot requires compiler/backend/toolchain design, exporting `bb_recomp_init`, respecting Win64 ABI, TLS/SEH/atomic and memory rules, and validating the generated library with genuine gameplay differential tests. The generated game code must remain **private on the player's machine**.
- Even a full 240,978-function recompiled library still calls into **PS4 compatibility services** in `bloodborne-runtime` for kernel, files, networking and graphics. The final requested true port must remove such guest PS4 runtime dependencies, replace graphics at engine API level and run without an ELF or derived binary *at runtime*. It can build game source locally during installation, but must use native Win32/PC runtime when launched.
- A passing synthetic PE DLL is not Bloodborne boot, gameplay, DLC, save safety, 5-person co-op or server delivery. No changes to Fornex, game data, security credentials or PR merges.

## Build

```
cmake -S native/source-port/recomp-v187 -B build-v187 -DCMAKE_BUILD_TYPE=Release
cmake --build build-v187 --config Release
ctest --test-dir build-v187 -C Release --output-on-failure
python native/source-port/recomp-v187/check_upstream_abi.py \
  --upstream-root /public/checkout/of/bloodborne-recomp \
  --project-header native/source-port/recomp-v187/recomp_abi.h
```

The output of the source guard explicitly includes `upstream_windows_x64_game_library_builder_ready:false` while the actual upstream code is macOS ARM64-only. The guard only reads publicly available source and emits bounded booleans, no full GitHub logs or any user-game data.

## Why this direction beats another compatibility wrapper

`bloodborne-recomp` (README and `docs/RECOMPILATION.md`, 2026-10-28 progress) reports **240,978 / 241,821 game functions running as compiled ahead-of-time C-derived code on ARM64** and **99.1% of executed recompiled instructions implemented directly in C**, against the remaining interpreter/translator fallback. Only **933 functions** have call-by-call recording checks. The goal for our **Windows native source port** is to adapt that real generated-code path to Win64, independently verify what it does, and then progressively replace *platform* calls and draw-level graphics.

This represents a much larger potential source-code foundation than decompiling 150,000+ functions manually, although **automatically generated C** is not the same as human-readable C++ decompilation and is not automatically independent of the PS4 ABI. `Paleblood` and `bbhost` are useful parallel semantic reconstruction and renderer donors. Do not conflate their progress counters.
