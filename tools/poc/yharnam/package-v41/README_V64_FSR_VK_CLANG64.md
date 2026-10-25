# V64: pinned AMD FidelityFX Vulkan backend CLANG64 compile repair

Scope: **source-only**, draft Windows native game candidate; no Fornex, retail game files or player saves are touched.

## Evidence
- GitHub Actions full Windows game run `40215100069` failed in the pinned FireBurn/FSR-Vulkan `ffx_vk.cpp`, **not** in the V63 fixed `_countof` files.
- First real failure was `new (&backendContext->uniformBufferMutex) std::mutex()` requiring standard header `<new>`.
- Second failure was `floor(log2(...))` without declared `log2`. C++17 `<cmath>` and `std::floor(std::log2(...))` are portable.
- Pinned dependency: `FireBurn/FSR-Vulkan` SHA `c64f093404125e960813f95f1996c14780f0dd69`, native file `upstream/ffx-1.1.4/sdk/src/backends/vk/ffx_vk.cpp`.
- Verified the original AMD source has exactly one Vulkan header anchor, one placement-new call and one `floor(log2(` expression.

## Change
- Extend the original fail-closed `patch_fireburn_clang64.py` to validate **all four** AMD host C++ units before writing any file.
- Add only `<new>`, `<cmath>` and the qualification `std::floor(std::log2(...))` to a copied **pinned** vendor translation unit.
- Extend Python tests to reject unexpected call sites and accidental double patch.
- Update both rapid Windows CLANG64 smoke and the full candidate workflow to compile the **actual Vulkan backend** with the full generated shader include paths before starting the slow native GPU build.

## Gate
A successful **small Vulkan smoke** only demonstrates this translation unit compiles with the selected compiler and dependency revision. A new successful full Windows game build, complete EXE/ZIP packaging and actual gameplay QA must still be independently verified. Do not present CI-only files as a playable release or deploy to Fornex.
