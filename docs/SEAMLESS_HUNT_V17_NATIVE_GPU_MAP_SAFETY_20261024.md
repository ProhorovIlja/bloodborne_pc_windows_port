# Seamless Hunt V16/V17: native GPU map safety + texture GC guards

Date: 2026-10-24. Development branch: `feature/yharnam-dedicated-server-poc`.
Pinned client source: `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`.
Status: **source patch prototype integrated into the atomic composer, not a released or runtime-verified Windows client.**

## Why

Player reports:
- VRAM steadily rises over long sessions **with frame generation disabled**; FG-only explanations are insufficient.
- A co-op friend sometimes crashes when opening the map.
- Long-session FPS degradation and occasional graphics artifacts.

Related external fixes:
- Mrsuss60/bloodborne_pc_windows_port PR #89 / commits `0144b5c`, `89f0521`: reclaim depth targets, guard in-use resources and adjust GC scan quotas.
- visy/bloodborne_pc_windows_port: a newer policy and active-bound protection.
- These implementations use different image-cache structures. **Do not replace pinned texture_cache.cpp wholesale.**
- Existing pinned GC performs emergency eviction and writebacks; changing GC aging aggressively can create thrash and image corruption.

## V16 (actual native C++ source transformation)

`tools/poc/yharnam/map-safety-v16/patch_map.py` edits `bbport/gpu/shim/bbport_map_3d.cpp` only:
1. Releases VMA buffers when creation succeeds but the mapped pointer is null. Two separate allocation paths were affected.
2. A cached render target is not considered valid without a live ImGui Vulkan texture descriptor.
3. A failed descriptor allocation releases the created color and depth attachments and resets their dimensions so the next attempt can recover.
4. Rejects invalid chart dimensions / pixel spans / non-finite zoom and clamps the **optional map render viewport** to at most 4096 pixels per axis. Gameplay resolution is unaffected.
5. All transformations refuse drift from seven anchored source segments and do not change the source file in place.

## V17 (actual native C++ source transformation)

`tools/poc/yharnam/gc-safety-v17/patch_texture_gc.py` edits `bbport/gpu/shadps4/video_core/texture_cache/texture_cache.cpp` only:
1. Protects images still bound for shading, active render targets, presentation surfaces and live scene proxies from eviction.
2. Keeps existing GC timing, pressure limits, writeback and deletion quotas.
3. Adds experimental aged depth-image reclaim only when `SH_GC_RECLAIM_DEPTH=1`. **OFF by default.** Runtime compatibility with graphics fixes is not yet proven.

## Composition and CI

Integrated after V14 in `tools/poc/yharnam/unified-v9/compose_sources.py`.
The `test_compose.py` fixture now includes V16/V17 source signatures and drift tests.
The `.github/workflows/shyt-v15-source-safety.yml` gate includes:
- V15 active XML-patch safety;
- V14 quit/performance diagnostics;
- 6 V16 and 4 V17 Python unit tests;
- full unified source-composition fixtures;
- immutable upstream source download / transformation smoke checks;
- V14 C++ telemetry tests.

**Evidence verified in this session:** 6/6 V16 isolated tests, 4/4 V17 isolated tests, 4/4 V15 isolated tests, C++20 V14 performance watch test; seven V16 source anchors and the V17 GC anchor exist in the pinned upstream. Actual unified composer suite / GitHub Actions have NOT yet been observed running successfully (connector-made commits may not trigger Actions). No Windows game compile, two-player game test or VRAM leak elimination is claimed.

## Validation required for release

- Build one version-pinned Windows client with the full source composition and preserve the previous known-good build for rollback.
- Run the same 45–90 minute route repeatedly through several large areas without frame generation and with matching texture/render settings; record actual driver GPU budget/usage, effective GC usage, texture image bytes, process RAM, frame-time percentiles, and GC evictions.
- Open/close the 3D map 20+ times, repeat while joining friends, alt-tabbing and changing resolution, and check for blank textures, failed descriptor allocation, GPU device lost and crashes.
- Test low (4–6 GB), mid (8 GB), and high VRAM cards separately; do not enable stale depth reclamation outside a dedicated A/B profile before data supports it.
- Investigate crash dump call stacks before assigning the player's map crash specifically to V16; map and network interactions can also fail elsewhere.
- Production CLS services / Fornex ports must remain untouched.

This change is an incremental compatibility and correctness improvement, not a native Windows gameplay release.
