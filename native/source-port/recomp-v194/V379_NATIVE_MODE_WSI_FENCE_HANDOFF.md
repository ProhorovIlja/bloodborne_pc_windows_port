# Native V379 — enumerated OS modes and GPU-fence-safe target retirement

Date: 2026-11-12. Based on V378 `feature/native-v378-x64-dynamic-display-20261112`.
Scope: **source-only portable C11 contract** for the future independent PE32+/ELF64
Bloodborne engine. Not an operating game, not a GPU backend and not evidence of a
completed no-EBOOT AOT recompilation.

## Source changes

- `native_present_guard_v379.{h,c}` accepts a **bounded** list (up to 1,024)
  of caller-verified fullscreen modes. It selects exact physical pixel width
  and height, and rational refresh; 60/1 and 60000/1001 are not conflated.
  If refresh is unspecified, it selects the highest available at the exact
  resolution. A nonenumerated mode never silently falls back.
- Surface validation requires explicitly queried format/colorspace, usage
  and present support plus actual backend pixel and extent bounds. It
  distinguishes current fixed extent, unspecified extent and zero-sized
  minimized surfaces; it rejects a one-dimension fixed/undefined mismatch.
  It performs no SDL, DXGI, Vulkan or D3D12 calls.
- Render target generations track a single retired allocation and a monotonic
  submitted/completed GPU-fence timeline. A resize cannot overwrite a
  still-owned retired generation. Old allocations cannot be declared safe
  to free until their latest submitted fence completes; caller must destroy
  them through its actual GPU backend and then acknowledge destruction.
  Matching allocation keys stay reused without changing generations.
- Source is cross-platform, C11, bounded, does not include copyrighted
  Bloodborne assets/ELF/SELF/eboot or third-party proprietary SDK files.
- `test_native_present_guard_v379.c` exercises 60 vs. 59.94 Hz,
  3440x1440/5120x1440, invalid mode lists, unsupported/missing capabilities,
  minimized and mixed extents, repeated resizes, stale/forward GPU fence
  values, safe retirement and exact-key reuse.
- CI is native Windows clang-cl and Linux GCC/Clang, including ASan/UBSan.

## Upstream source review (no blind imports)

- SDL3 `SDL_GetFullscreenDisplayModes`: list is per-display, must be
  freed by SDL_free and called from the main thread.
  https://wiki.libsdl.org/SDL3/SDL_GetFullscreenDisplayModes
- SDL3 `SDL_DisplayMode`: density and exact refresh fraction must be kept
  distinct; use physical pixel dimensions from the backend rather than
  assuming logical window size equals swapchain extent.
  https://wiki.libsdl.org/SDL3/SDL_DisplayMode
- Vulkan `VkSurfaceCapabilitiesKHR`: currentExtent can be an undefined
  UINT32_MAX pair; its min/max extents, supported image use and queried
  formats are device/surface-specific.
  https://docs.vulkan.org/refpages/latest/refpages/source/VkSurfaceCapabilitiesKHR.html
- Windows WSI may require current swapchain dimensions to match the actual
  surface pixel size; a minimized 0x0 window needs a deferred recreation.
  https://docs.vulkan.org/spec/latest/chapters/VK_KHR_surface/wsi.html

## Strict outstanding integration work

1. Bind the structures to **real** SDL3 display IDs, per-monitor DPI,
   Win32 DXGI swapchain caps and Linux Vulkan WSI query results. Reenumerate
   on monitor/driver change; handle HDR/SDR colorspace selection separately.
2. Connect target generations to D3D12/Vulkan actual synchronization and
   device-loss paths; confirm that all queues, captures and UI references
   have released the retired image BEFORE acknowledging GPU destruction.
3. Implement native executable/entrypoint from the independently verified,
   complete owner-data AOT and fully native host imports. Original runtime
   EBOOT/SELF/ELF and shader/CPU guest translators are forbidden by target.
4. Complete original gameplay, physics, AI, maps, animation, audio, DLC,
   saves, online and hardware validation before any 'playable native port'
   claim. Keep playable BBPort/Yharnam Together separate until verified.

This is NOT proof of native original-game startup or performance on actual
displays; public CI cannot and must not load original commercial game files.
