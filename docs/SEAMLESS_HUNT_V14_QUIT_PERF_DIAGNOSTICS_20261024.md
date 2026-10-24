# Seamless Hunt V14: Quit to Desktop + long-session performance investigation (2026-10-24)

Source gate only, NOT a tested native Windows game release. No production Fornex or CLS changes.

## Already in pinned upstream, verified against lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15

- bbport/gpu/shim/bbport_overlay.cpp already implements a Quit to Desktop row near the bottom of BBPort settings; holding L3+R3 ~1.5s also raises a confirmation box.
- QuitBox saves BBPort settings and dispatches SDL_EVENT_QUIT. bbport/gpu/shim/window.cpp handles the event by leaving the window loop, rather than forcibly terminating the process.
- Existing GPU telemetry in bbport_toggles.h: live image count and size, vk_image_bytes, GC trigger/usage/freed. Vulkan texture cache already has a collector, and pipeline-cache code has background cache saving. A long-session slowdown is NOT yet confirmed as a leak.

## V14 actual code

- tools/poc/yharnam/quit-perf-v14/patch_quit_perf.py patches one pinned bbport_overlay.cpp AFTER the Spectator V13 patch; all seven exact anchors independently verified.
- A prominent Quit to Desktop button appears in the Yharnam Team/title screen and in the Team screen opened from the game's System menu. F10 invokes the SAME confirmation dialog even without opening the BBPort settings. Cancel is the default choice. It does not synthesize save events or exit(0). The existing Settings -> Quit row remains unchanged.
- F9 toggles an opt-in passive diagnostics overlay. Fixed-size 36-sample array, one sample every ~10s, no heap allocations, no Vulkan flushes, no automatic cache resets. Shows present frame ms, resident process bytes, registered live images, GPU image bytes, GC count, ImGui texture count. Prints one SH-PERF log line about every minute while enabled.
- To avoid false conclusions, frame-time drift is compared only after >=2min and only if every sampled map ID is the same. Working-set growth is only a diagnostic clue. Shader compilation, storage stalls, frame pacing or remote/network issues may also produce time-dependent lag.
- tools/poc/yharnam/unified-v9/compose_sources.py now applies V14 AFTER V13; default-branch GitHub Actions source gate checks the patch and builds/runs standalone C++ unit tests. No remote GitHub Actions result confirmed.

## Local validations

1/1 CTest Release native bounded Watch tests PASS, 4/4 Python patch tests PASS. 7/7 pinned upstream insertion anchors verified in GitHub. The real Windows overlay and full game were not compiled during this step. The user's long-session slowdown is not fixed/diagnosed yet.

## How to collect an actionable report once a compatible V14 native Windows build exists

Press F9 during a stable play session and keep it active for at least 10-20 minutes, ideally revisiting the SAME map without tabbing between areas. Logs contain SH-PERF lines showing RSS, GPU image memory, image count and frame times. Capture GPU model, driver, resolution, upscaler, frame generation state, players, mods and duration; do not upload account credentials or saves.

- Rising RSS but stable GPU resources: investigate CPU/host memory and network/event queues.
- Rising live GPU images / GPU image bytes: inspect texture-cache GC, map art lifetime, buffer cache, driver allocation.
- Stable memory with frame-time deterioration: inspect shader/pipeline jobs, GPU waits, CPU scheduling, frame generation/present pacing, driver thermals/power, IO and co-op tick queues.
- Slowdown only during online multiplayer: examine queue depths, retransmission/backpressure and worst-peer RTT before blaming graphics.

Never flush all pipelines/textures on a timer or force close during a game. Keep the existing CLS and protocol-7 Fornex test service live until a fully paired client/server build passes real tests.

Developer code: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/tree/feature/yharnam-dedicated-server-poc/tools/poc/yharnam/quit-perf-v14
Source-gate CI: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v9-source-gate.yml
## Root-cause leads from current Supermedo native Windows releases (verified 2026-10-24)

Official Supermedo v1.9.1 (2026-10-17) documents FPS drops after deaths/area loads; v1.9.2 (2026-10-18) fixes a genuine FSR 3.1 frame-generation VRAM leak; v1.9.3 (2026-10-21) reduces staging memory and reverts 1.9 GPU layer to earlier stable GPU logic. Latest official changelog lists v1.9.4 on 2026-10-21. Sources: https://bbport.de/changelog/ and https://github.com/Supermedo/bloodborne_pc/releases .

We compared latest `Supermedo/bloodborne_pc` windows branch against pinned `lKaniel/bloodborne-server@77e3507` for:
- `gpu/shadps4/video_core/renderer_vulkan/vk_frame_generation.cpp` (different implementation, not a safe one-file copy)
- `gpu/shadps4/video_core/renderer_vulkan/vk_presenter.cpp`
- `gpu/shadps4/video_core/renderer_vulkan/vk_staging_buffer_pool.cpp`
- `gpu/shadps4/video_core/texture_cache/texture_cache.cpp`

Pinned Yharnam code uses `ffxVkPortableFrameGenerationContextDestroy` while the current Windows branch uses `ffxVkFsr3_3_1_6FrameGenerationContextDestroy`, and the presenter/cache implementations differ considerably. A blind replace would likely break co-op and/or graphics. Next task is transplanting *semantic fixes* into our pinned native path with targeted source diff, compatibility tests and long-session benchmark. **Do not claim fixes are already incorporated into V14**. Immediate A/B check on the current build: toggle FSR3 frame generation off while keeping the same map/scene, and compare VRAM/frametime over time; it is a diagnostic, not a final workaround.

The relevant pinned Yharnam staging pool already has a 30-second idle timeout and 512 MiB default keep budget (comments in `vk_staging_buffer_pool.cpp`), whereas current Supermedo release reports a changed staging retention policy. Do not change its constants without measuring burst stalls vs footprint.
