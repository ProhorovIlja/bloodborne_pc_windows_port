# Native V380 — Win32 ≠ 32-bit; Windows/Linux/macOS host and renderer contracts

Date: 2026-11-12. Base: `feature/native-v379-mode-wsi-retirement-20261112`, PR #109. New draft PR V380 is source-only; it does not boot Bloodborne.

## Why this exists
Microsoft defines _WIN32 on native Win64 builds. _WIN64 distinguishes 64-bit Windows code; _M_X64 identifies Windows AMD64 and _M_ARM64 identifies Windows ARM64. PE32+ is the 64-bit Windows image format. Linux native x64 binaries are ELF64. macOS binaries are 64-bit Mach-O (AMD64 or ARM64).

The PS4 Bloodborne retail game executable is already AMD64 ELF64. Its original game logic needs independently verified host OS recompilation, host imports, linker closure, and 100% offline game execution **without** a guest interpreter/translator/eboot/SELF/ELF runtime. Apple Silicon ARM64 requires another instruction-set compilation target; running AMD64 with Rosetta would violate strict native ARM64 target.

## New source
- `native_platform_caps_v380.h/.c` detects compile-time host OS (Windows/Linux/macOS), x64/ARM64, native file-format class and pointer bits. It rejects 32-bit/unknown hosts.
- Per-platform renderer whitelist: Win D3D12 or Vulkan, Linux Vulkan, macOS Metal or Vulkan via tested portability driver. This is a policy only; does not instantiate any renderer.
- A renderer can be selected only if an actual backend supplies validated device/surface/shader readiness and feature flags; all optional features (FSR, DLSS, XeSS, Reflex, XeLL, HDR, VRR, dynamic resolution, frame generation) default off until explicitly verified by vendor SDK/driver/monitor capability. Required features are fail-closed. Optional features are recorded as disabled if unsupported. Choice is not altered on failure.
- Caller may request one backend and opt into fallback; Windows prioritizes D3D12, Linux Vulkan, macOS Metal if no preference. The actual hardware/SDK gate is not implemented here.
- `test_native_platform_caps_v380.c` covers host identity, _WIN32 x64 semantics, renderer OS whitelist, request validation, missing/duplicate backend probes, missing initialization/surface/shaders, optional versus mandatory feature behavior, invalid feature bits, no mutable output on failure and fallback.
- GitHub Actions builds tests with GCC/Clang and sanitizers on Ubuntu, clang-cl on Windows x64, clang on macOS Apple Silicon. Success proves only these C11 contracts compile and test, not original-game macOS port status.

## New 2026 Khronos verification
https://vulkan.org/porting
Khronos says MoltenVK is deprecated and maintained best effort as of 2026. For Apple Silicon macOS, Khronos recommends KosmicKrisp (via LunarG macOS Vulkan SDK or Mesa); MoltenVK remains relevant on Intel-based Macs. No Vulkan portability feature may be assumed universally. A future native Metal renderer may better target Apple Silicon than a Vulkan portability layer; benchmark each.
SDL3 supports Windows, Linux and macOS window, input and graphics integration: https://wiki.libsdl.org/SDL3/FrontPage
Win32/_WIN64 meaning: https://learn.microsoft.com/en-us/windows/win32/winprog64/the-tools

## Priority and strict claims
P0 complete independent original game AOT, engine entrypoint and native imports. Current V379/380 source is not gameplay, renderer, full native game startup, simulation, original 60Hz physics parity, or user feature-ready client.
P1 real D3D12 and Vulkan hardware backends, host SDL3/display/DPI lifecycle, asset streaming, FLVER skeleton/animation, GPU resource management, shader caches, frame pacing, anti-corruption, device-loss handling.
P2 real input/OS event integration, remappable chords/jump, controller hotplug, scalable HUD, accessibility and safe saves/NG+.
P3 optional validated FSR/DLSS/XeSS/Reflex/FG, HDR/VRR, region/server options, LAN/P2P/dedicated online, launcher with rollback and signed manifests. Never claim zero latency or guaranteed frame times.
P4 macOS Apple Silicon ARM64 recompilation (not x86-64 native), Metal or verified Vulkan portability, no assumed NVIDIA-specific SDK features; additional legal and platform-specific testing.
P5 verify all claims with owner-controlled private original-game data and actual machines before native port release. Keep copyrighted game assets out of public GitHub/CI.

No upstream source code or proprietary SDK was copied. V380 is an architectural portability foundation, not a release claim.
