# Native V366: fence-owned upload staging; Proton/Linux research; ultimate feature contract

Date: 2026-11-11. Base: V365 Draft PR #95.
Branch: feature/native-v366-fence-ring-proton-research-20261111.
This document records the user's requested *native Windows and Linux* Bloodborne port with an extensive later remaster-style feature set. It **does not** claim to implement those later features.

## Defining invariant: no PS4 executable at runtime

The final native Windows/Linux programs must not load, execute, map or interpret an original PS4 EBOOT/ELF/SELF or require PS4 kernel/GNM/HLE as a guest at runtime. A user-owned original game executable may be inspected **offline at build/recompilation time** for provenance and function reconstruction; generated user-owned outputs should remain local/private. Game asset data may remain on user-owned disk. No game binaries, code derived from owner-provided game builds, encrypted key material or game assets belong in public GitHub or CI.

A "Bloodborne.exe" that still loads PS4 guest code (as most BBPort/launcher forks do) is not the source-native target. Similarly, a Linux binary that must launch under Proton is not the requested native Linux deliverable.

### Platform matrix and Proton's useful role

| Path | Windows | Linux | Final dependency? | Correct use |
| --- | --- | --- | --- | --- |
| Native engine + D3D12 | Primary Windows graphics option | Optional Windows exe under Proton via VKD3D-Proton | No for native Linux | Back-end validation, performance reference and temporary fallback |
| Native engine + Vulkan | Optional Windows graphics option | Primary native Linux graphics option | Yes for Vulkan renderer, not Proton | Vulkan-first cross-platform graphics, Linux direct executable |
| Proton/Wine | Not applicable to native Windows launch | Windows build compatibility and smoke-test route | No | Alternative support path, CI and cross-validation; not a substitute for native Linux code |
| DXVK | D3D8/9/10/11 → Vulkan | Same through Wine | No | Learn driver workarounds, cache/pipeline handling; our chosen D3D12 path is not DXVK |
| VKD3D-Proton | D3D12 → Vulkan | Windows D3D12 build under Proton | Optional testing only | Compare WARP/native D3D12 with Vulkan translation, not host-game AOT |
| gamescope | N/A | Optional SteamOS/Linux compositor | No | Frame caps, VRR, HDR, scaling and presentation tests |
| Steam Input | Optional external remapping | Optional external remapping | No | Complement in-engine SDL3 mappings and fully rebindable controls |

The native Linux executable should use native OS APIs (or thin cross-platform libraries such as SDL3), and Vulkan directly. Preserve native fallback paths for Vulkan extensions. Proton's implementation and its forks remain **donor research / testing references**, subject to license compatibility.

Repositories scanned (specific research, not a claim to index every GitHub repository):
- https://github.com/ValveSoftware/Proton (proton_11.0; Wine, DXVK, VKD3D-Proton)
- https://github.com/doitsujin/dxvk (D3D8/9/10/11 Vulkan)
- https://github.com/HansKristian-Work/vkd3d-proton (D3D12 Vulkan)
- https://github.com/ValveSoftware/gamescope (Linux/SteamOS presentation)
- https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator (native Windows D3D12 memory pooling, MIT)
- https://github.com/GPUOpen-LibrariesAndSDKs/FidelityFX-SDK (FSR upscaling / frame generation, D3D12 and Vulkan, version and hardware dependent)
- https://github.com/intel/xess (XeSS / XeLL, version and GPU support check)
- https://github.com/NVIDIA-RTX/Streamline (DLSS, Reflex, feature availability and SDK licensing)
- https://github.com/libsdl-org/SDL (SDL3 input and gamepad mapping)
- https://github.com/KhronosGroup/Vulkan-Docs (validation and pipeline-cache/generation rules)
- https://github.com/Yharnam-Hunters/Paleblood (renderer batch/fence lessons; #463, #595)
- https://github.com/droogie/bbhost (GPU memory, network and scheduling bug patterns; #204 and #73)
- https://github.com/bloodborne-native/bloodborne-recomp, https://github.com/Astrr00/BloodbornePC (offline static recompiler candidate routes)
- Existing native V360–V365 branches and owner-private Bloodborne CUSA03173 / DS3 PC resources.

Current public projects/libraries evolve: pin revisions for builds, inspect source licenses per file and do not assume one upstream's reported fps/CPU benchmark transfers to our native Windows/Linux runtime.

## Implemented in this PR: V366 GPU-fence staging ring

Code: native_fence_upload_ring_v366.{h,cpp}. This is a CPU-side **ring scheduler** of offsets in a caller-owned persistently mapped GPU upload buffer. The scheduler does not own a GPU allocation, actually submit work, read game data, or create a renderer. It complements V365's existing actual D3D12 UPLOAD → DEFAULT buffer upload. When integrated into production, one renderer context/queue must own its ring and fence, and command allocators/descriptors must be retired under the same fence watermark.

Safety properties:
- Hard upper bound 256 MiB per ring; no heap allocations in the scheduler; maximum 256 outstanding submissions.
- Reserve uses power-of-two alignment 1..65536 and ensures no physical upload slice crosses the ring wrap boundary.
- Strict single active (uncommitted) reservation; commit only after successful GPU submission with a strictly increasing fence, or cancel before submitting. Reservation tokens prevent accidental stale commit/cancel.
- GPU-completed fence numbers retire records in submission order. A stale watermark cannot falsely free in-flight allocations; wrap reuse occurs only once preceding fence work is known complete.
- UINT64_MAX is interpreted as D3D12 device-loss sentinel; fail closed without freeing in-flight allocations. Explicitly tear down the lost GPU device before reclaiming its upload memory. No automatic retry on device loss.
- Not internally thread-safe. Renderer job producers must synchronize before using shared queue/ring state.
- Failure never issues GPU or CPU memory operations. Caller must retain persistently mapped UPLOAD memory until fence retirement, even after source FLVER scratch is freed.

Tests:
- test_native_fence_upload_ring_v366.cpp: deterministic wrap, power-of-two alignment, stale token/fence, capacity, cancel, 256 pending slots, device loss, 50,000 randomized synthetic reservation scenarios with pairwise non-overlap verification.
- test_native_d3d12_upload_ring_v366.cpp: **real Windows D3D12 WARP GPU** two-flight copy. Stages 48 bytes at physical offsets 0 and 48, submits fence 1 and 2, refuses premature reuse, waits for fence 1, reuses offset 0 for a third 48-byte transfer at fence 3, then reads back GPU-default data and checks all 96 bytes against known invented patterns. Holds command lists and allocators alive until completion.
- native-v366-fence-upload-ring.yml: Ubuntu GCC/Clang/ASan/UBSan and Windows clang-cl + WARP real GPU readback. No private assets.

Evidence limits: this does not yet mean that V365 uses the ring in production; it is independently exercised on real Windows WARP. The next integration must share staging heaps/allocator/fence with a rendering scheduler, not simply concatenate separate upload tickets. No hardware GPU frame-time wins, shaders, full render, simulation, online or game boot are claimed.

## Ultimate product backlog — build only behind correctness gates

### P0 — independent game executable and baseline offline correctness
- Full CUSA03173 1.09 executable AOT/source reconstruction at build time, with **zero guest interpreter fallback at runtime**, native startup and import/callback closure; native Windows and Linux executable releases.
- Stable original gameplay: full base game and The Old Hunters, enemy/AI/physics scripts, items/progression/events, checkpoints, cutscenes, dialogue, audio, full save compatibility and recovery, achievements/trophies remap, accessibility and mod-aware file safety.
- Deterministic simulation with correct 30/60+ Hz handling. Decouple render display interpolation from game simulation to avoid physics bugs and speed-dependent combat; full offline playthrough tests before broad features.
- Asset streaming: asynchronous read/decompression, priority by visible region/animation, bounded staging and file cache budgets, memory residency accounting, cancellation, age/priority eviction, integrity-checkable game files, no direct unverified asset pointers on the GPU. Add streaming benchmark scenes and memory-pressure regressions.

### P1 — native rendering, latency, stability and anti-stutter
- D3D12 on Windows, Vulkan on Linux (and optional Windows Vulkan), explicit memory ownership, residency budgeting, proper GPU fences and pipeline cache; recover from device loss, alt-tab, suspend, window resize and low-VRAM cases.
- Shader/pipeline discovery and **warmup** only from user-owned asset shaders and known gameplay states; stable disk cache keyed by game/driver/GPU/renderer build, background compilation and progress indicator, precise invalidation. Neither eagerly compile all possible variants nor promise a universal zero-stutter result.
- Frame-time and input-to-photon instrumentation (p50, p95, p99/p99.9), frametime cap, CPU/GPU queue depth, dynamic resolution, VRR/V-Sync/triple buffering options, pacing that respects Linux compositor/Windows presentation semantics. Diagnose microstutter instead of marketing FPS only.
- Native anti-aliasing/reconstruction providers selected after capability checks: FSR 2/3/4 where officially supported, DLSS SR/DLAA/Frame Generation where SDK/GPU/driver permit, Intel XeSS/XeFG/XeLL where supported, native TAA, sharpening. Guard fallback paths and SDK licensing. **Frame generation changes displayed output cadence, not network latency or underlying simulation speed.**
- NVIDIA Reflex via supported native D3D12/Streamline integration on Windows and VK_NV_low_latency2 on Vulkan where present; Intel XeLL, AMD latency options when supported; don't expose bogus toggles on incompatible hardware.
- Graphics/gameplay correctness: texture compression, anisotropy, SSR, SSAO, shadows, effects, motion vectors, native ultrawide/UI scale, HDR only if color pipeline/OS/GPU verified, optional reshade/mod support without client corruption.

### P2 — PC controls, accessibility and quality-of-life
- SDL3 keyboard+mouse and gamepad backends, raw/high-resolution mouse input, relative camera motion, frame-independent smoothing, gyro/rumble where device supports it, deadzones and adjustable curves. Support Xbox/PlayStation/Nintendo/Steam Input and generic HID; detect and show appropriate prompts.
- Per-action remapping including **Shift+key / Ctrl+key / multiple-button chords** and gamepad combinations; binding conflicts, context-sensitive layering and guaranteed way to navigate settings. Allow modifiers with hold/tap behaviors without accidental dodge/jump inputs.
- Dedicated jump action independent of dodge/running with configurable controller input (e.g. L3, B/Circle, custom chord) and custom keyboard key; preserve original action availability as selectable option.
- Configurable HUD button glyphs (PlayStation/Xbox/Nintendo/KBM), prompt remaps, hot-swapping inputs, high-DPI UI, colorblind and accessibility presets, subtitles, customizable FOV/camera if correctness proven.
- Manual NG+ selection *after clear* with reversible confirmation and automatic save backup/restore; avoid difficulty/progression softlocks. Optional level respec, equipment sorting, expanded UI and gameplay QoL behind separate opt-in settings.
- Mod loader and safe override directory after full-game correctness; hot-reload only for resource types proven safe.

### P3 — online and co-op after authoritative offline foundations
- Host/self-host/dedicated server profiles, local/LAN/localhost, region/server browser, clear ping/jitter/loss, friends/invite/password sessions, quick match and invasions, compatible save/progression/quest sync, transparent host migration and reconnect where feasible.
- Transport design evaluated rather than guessed: encrypted/authenticated reliable control channel, tick-aware unreliable movement snapshots, NAT traversal with fallback relay, backpressure, rate limiting and DoS safeguards, interest management and state-reconciliation; measure under packet loss and 20–250 ms delay. A goal of **zero internet latency is physically impossible**. Optimize overhead and tail latency, not just average ping.
- Separate matchmaking/session protocol version from native game build. Support LAN without mandatory internet; dedicated server deploy through reproducible containers with safe rollout/migrations, minimal log data, protected secrets and save compatibility.
- Instrument server CPU/memory per concurrent player, p50/p95/p99 tick lag, desync rate, join success, latency, packet bytes; evaluate regression gates before publishing "best possible" claims.
- Optional Discord Rich Presence (BBSC: Yharnam Together styling, location, compact BL/build), player visibility/ping/name HUD toggles, co-op/invasion colors, chat toggles, and other prior Ultimate requests only when core gameplay is stable.

### Release and quality gates
- No gameplay feature promoted without repeatable tests on **Windows and Linux**, GPU vendors, real owned game assets locally and complete representative playthroughs.
- Separate latency, crash rate, memory load, long-session leak, shader compile hitch, and network metrics; keep a known-good rollback build and save migration tests.
- Avoid copyrighted uploads, private save/log publication, and unsupported vendor binaries. Check SDK redistributability and upstream license for every imported component.
- Maintain two tracks: (1) correct whole-game AOT/runtime closure and (2) native asset/render/IO infrastructure, with full-playable offline at their intersection. Later features follow, not substitute for the executable.

## Immediate next engineering task after V366

Integrate the fence ring with a shared long-lived D3D12 upload heap and command-batching queue; prove multiple resource uploads and retirement without per-file blocking fence waits, and measure memory/CPU overhead on physical GPU. In parallel, implement native Vulkan upload resources and sync for Linux, then a shader/material/mesh render smoke. Maintain the separate original-game AOT status dashboard and identify the most blocking unresolved interpreter/import dependency before focusing on nonessential extras.
