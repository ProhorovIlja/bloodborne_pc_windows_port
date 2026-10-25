# V65: CLS MinGW FidelityFX global `_countof` backport

This corrects an ACTUAL full native Bloodborne Windows renderer build failure, not a hypothetical portability issue.

The original V64 run https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40230955579 eventually **FAILED**. Its compiler log repeatedly reports seven undeclared Microsoft-only `_countof` references in AMD FSR3's `sdk/src/components/fsr3upscaler/ffx_fsr3upscaler.cpp` (not the frame interpolation or optical flow units patched earlier). The job repeated the same diagnostic for roughly 165 minutes before step timeout. **No playable EXE or downloadable release resulted.**

During the user's requested external fork comparison, CLS's October 2026 PR https://github.com/lKaniel/bloodborne-server/pull/412 was discovered to contain `bbport/gpu/patches/fsr-vulkan/0004-ffx-types-countof-for-mingw.patch`. This patches the AMD 1.1.4 shared host `ffx_types.h`, not just one source file. Its `#if defined(__MINGW32__) && !defined(_countof)` guard provides a strictly Windows-MinGW-only array count helper using `sizeof(array)/sizeof(array[0])`.

Our V65 ports the same guarded compatibility definition into the exact pinned `FireBurn/FSR-Vulkan` submodule `c64f093404125e960813f95f1996c14780f0dd69` through `patch_fireburn_clang64.py`. The script validates **five** files as one transaction (existing FSR log/optical/frame/Vulkan backend plus `ffx_types.h`), refusing an unexpected vendor source revision or duplicate patch before writing any. The previously tested safe `std::size` conversions in frame interpolation and optical flow remain intact. Other compilers are unaffected by the guarded fallback.

Added a focused `ffx_fsr3upscaler.cpp` Clang64 `-fsyntax-only` compile before expensive native renderer build in **both** smoke and real-client CI. A Python regression tests exact macro, guard, reapply failure and source drift.

- Smoke CI: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v63-native-fsr-clang64-smoke.yml
- Full native Windows build: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v63-native-game-candidate.yml

**No game assets, saves, live Fornex, shadNet server or `master` are modified**. This is a DRAFT PR #20 on `feature/shyt-win-fsr-countof-v63`; it is not a guarantee that later native renderer files compile, link or work in a real two-player game. Check CI before claiming success.
