# Native V377 — strict PE/ELF AOT static preflight and 60 Hz simulation / unlocked rendering contract

Date: 2026-11-12. Stacked on Draft Native V376. Branch `feature/native-v377-aot-closure-fixed60-20261112`.

## Mission and accurate current status

The requested final product is **an independent native Windows x64 and native Linux x86-64 Bloodborne client** that executes neither original PS4 EBOOT/ELF/SELF nor guest CPU interpreter/JIT, Orbis ABI/HLE or GNM/PM4 GPU packet translator at runtime. Offline build-time/source-port extraction from a user-owned original v1.09 image may be separately supported privately; no private game bytes belong in public CI/repo. The complete offline game, DLC, chalices, physics, AI, story/events, save/load and audio must work before labeling it playable. Windows D3D12 and Linux Vulkan independently render invented FLVER-like triangles, not the game itself. V376 validates a bind pose and synthetic skinning, not HKX animation.

The AOT path ALREADY has bounded private probes and host-native synthetic components: V207 checks scanner→generated AOT registration; V287 audits native AMD64 COFF objects and unresolved external symbols; V309 runs a private linker diagnostic with `/NOENTRY` (a DLL, **not** a working game). V377 does not replace those proofs or falsely claim that the private game is fully recompiled. V377 introduces a different strict gate: inspect final **binary container architecture, executable entry and statically declared dynamic imports** for PE32+ and ELF64, before any game-boot promotion.

## Implemented in V377: independent static binary closure preflight

Files: `native_binary_closure_gate_v377.py`, `test_native_binary_closure_gate_v377.py`, `native_synthetic_host_v377.c`.

- No Python packages required. Strict size limit 512 MiB, safe file reads and bounds checks. Refuses symlinks, invalid file sizes/sections/program headers, original PS4 ELF type, non-AMD64 targets, DLL-as-executable, missing executable entry, corrupted RVA/import directory, truncated symbols, unbounded/unknown libraries, nonnative interpreter paths and unreviewed RPATH/RUNPATH. Does not need to open original game data.
- Windows PE32+: verifies DOS/COFF/PE32+ structure, AMD64 machine, executable section containing entry, bounded import table, explicit reviewed native Win32/D3D12/Vulkan/SDL3 system libraries and Windows API-set DLLs. Rejects imports naming PS4/Orbis, shadPS4, Wine/Proton and unknown third-party libraries. Needs policy update after each **reviewed** legitimate library addition; a denylist alone is not sufficient.
- Linux ELF64: verifies x86-64 machine, ordinary executable/PIE type, executable PT_LOAD entry, bounded PT_DYNAMIC/DT_NEEDED/DT_STRTAB, vetted native Linux library names and the system x86-64 dynamic loader path (if present). Rejects PS4-type ELF, unknown or unreviewed libraries and RPATH injection.
- Output is only a bounded aggregate result: `native_container_verified`, `imports_reviewed`, `unknown_imports`, plus **explicitly false** `runtime_no_guest_proven` and `whole_game_boot_proven`. Never emit user-owned symbols, executable bytes, filesystem paths, hash fingerprints, game strings or raw loader errors. Presence of a native PE/ELF header does **not** prove that the executable does not dynamically load an EBOOT or use a bundled interpreter. This gate must be combined with runtime file-access tracing, imported library/source provenance, full AOT call closure, authenticated original-file build-time attestation, clean-machine launch and offline gameplay tests.
- Public Python synthetic tests create invented PE32+/ELF64 binaries and mutate import names, entry addresses, machine types, loader paths, RPATH and malformed tables. Cross-platform CI also builds, runs and inspects an **actual synthetic native Win64 EXE and Linux x86-64 ELF**, each using host libc, never the game.

## Implemented in V377: portable timebase prototype

Files: `native_frame_clock_v377.{h,c}`, `test_native_frame_clock_v377.c`.

The prototype is an integer **fixed 60 Hz simulation scheduler** independent of display/presentation. A 60 ticks/1,000,000,000 ns exact rational accumulator prevents per-render floating point timestep drift. Frame rendering may be capped to **30, 60, 120, 240 or 0=unlimited**. These are presentational controls only; the program must never accelerate or slow game logic because more/fewer frames are drawn.

Test cases simulate 10 seconds of display pacing at 30/60/120/240 and verify exactly **600 logical simulation steps** in all four cases, with per-frame steps 2/1/~0.5/~0.25 as appropriate. Also test pause/resume rebasing, changing caps, deadline fractional remainder, early deadline polling without drift, backward clocks, 250ms interruption refusal and bounded catch-up. Max catch-up 8 sim ticks per caller invocation and 30 pending ticks; an overload is reported rather than silently discarding simulation time. This is *not* a threaded game loop, verified physical 60Hz Bloodborne simulation, adaptive VRR timer or actual rendering FPS limiter. Actual OS high-resolution waits, GPU present/acquire timing, simulation interpolation, snapshot buffering and server tick scheduling require integration later.

### Desired user options and serious compatibility conditions

- **Gameplay simulation target:** fixed **60 ticks/s**. This is a target pending measured game behavior; fallback/compatibility per-subsystem **30Hz** may remain necessary. AI/physics, combat windows, i-frames, timers, lock-on/camera, elevators, ragdoll, grass/cloth/water wakes, blood splatter, particles, dialogue/cutscenes, scripted events and save timers must use explicit *time-based* or documented fixed-step clocks. Don't change 30 FPS original by setting a new cap and call it a timing fix.
- **Rendering modes:** 30 / 60 / 120 / 240 / unlimited, later arbitrary value (e.g. 90/144/165/360) with validation, per-display profile, VRR, V-Sync/adaptive sync, latency/queue depth controls, FSR/XeSS/DLSS/Reflex capability-aware toggles. Output FPS is not sim tick. At 30 FPS there are 2 sim steps per rendered frame; at 240 FPS 4 rendered frames per sim step, with optional interpolation. Motion vectors must reflect physical simulation timestamps rather than synthetic generated-frame cadence. Frame generation never increases simulation/network tick or eliminates internet propagation latency.
- **Pacing:** use monotonic high-resolution OS clocks; measure frame time p50/p95/p99/p99.9, input-to-photon metrics and queue latency under shader cache misses, async streaming, online packet loss, GPU reset and scene transitions. Prefer GPU present fence/timeline and compositor-driven deadlines rather than CPU busy-spinning. If game simulation cannot keep up, explicit overload/recovery is better than silent speed-up or unbounded catch-up.
- **Network:** separate render FPS from client prediction/sim ticks and authoritative server updates; test 30/60/120/240/unlimited clients together under jitter, rollback/correction and desync; select servers/LAN/localhost/dedicated later. No physically impossible zero-latency promise.
- **Controls/QoL retained:** SDL3 Windows/Linux raw mouse and keyboard chords (Shift+key and gamepad combos), configurable dedicated jump (L3/B/Circle or any remap), PlayStation/Xbox/Nintendo/KBM glyphs, manual NG+, camera/movement options, ultrawide/HDR, safe mods, shader warmup and D3D12/Vulkan memory pools remain in the longer-term V366 backlog. Don't let these displace full offline native game boot.

### Timing/graphics donor research: check before adapting

- [Bloodborne 60 FPS analysis / Lance McDonald](https://www.bloodborne-wiki.com/2020/05/bloodborne-60-fps-mod.html): original game 30 FPS design, higher-rate patch based on other Souls PC timing, 30Hz residual cloth/blood/elevator behavior. External patch is PS4 EBOOT-oriented and **not** the source-native Win/Linux engine solution.
- [yogesh1239/BB-Sprint-Fix-Patch](https://github.com/yogesh1239/BB-Sprint-Fix-Patch): experimentally addresses fixed per-frame sprint, camera/AI and 19 timers, with limited full-playthrough proof and specific original executable/patch conflicts. Treat each measured timer as test case, not copy binary code-caves into our native renderer.
- [Mrsuss60/bloodborne_pc_windows_port](https://github.com/Mrsuss60/bloodborne_pc_windows_port): v0.7.2 claims live FPS patching and cloth stabilization for a BBPort-compatible runtime; research input, not proof of our completely native source-engine timer.
- [droogie/bbhost PR #139](https://github.com/droogie/bbhost/pull/139): merged menu/presentation timing and GPU scheduling improvements. FPS median numbers are platform-scoped and not transferable without repeatable test scenes.
- [droogie/bbhost PR #163](https://github.com/droogie/bbhost/pull/163): closed **unmerged**, water wakes still 30Hz and presentation re-alignment at 60Hz are useful behavioral regression cases; do not mistake for an already merged improvement.
- [droogie/bbhost PR #73](https://github.com/droogie/bbhost/pull/73): open DLSS/FSR/Reflex work. Capability checks, licensing, frame generation motion vectors and latency measurement remain hard gates.
- [Gaffer on Games, Fix Your Timestep](https://gafferongames.com/post/fix_your_timestep/): independent simulation and display interpolation with catch-up bound; implementation uses exact-rational clock math for repeatable tests.
- [Khronos VK_KHR_present_wait](https://docs.vulkan.org/refpages/latest/refpages/source/VK_KHR_present_wait.html): optional native Vulkan presentation pacing capability with VK_KHR_present_id + swapchain, not assumed universally present.
- [NVIDIA Reflex SDK](https://developer.nvidia.com/performance-rendering-tools/reflex): low-latency render queue regulation and input latency metrics, verify supported OS/GPU API before enabling.
- [SDL3 gamepad mapping](https://wiki.libsdl.org/SDL3/SDL_AddGamepadMapping): portable device mapping to underpin action remap/input glyphs; separate per-action chord logic still required.

## The highest-priority true AOT closure blockers (as of research 2026-11-12)

Source: public `bloodborne-native/bloodborne-runtime/docs/layers/` and `bloodborne-recomp/docs/RECOMPILATION.md`, plus our own private V207/V287/V309 probes. **Source-reported progress is not independently verified full-game coverage**.

| Blocking layer | Evidence | Required genuine native resolution |
| --- | --- | --- |
| Original game entry and PS4 executable loader | `layers/executable.md` explicitly says 0%: EBOOT prepared, loaded at fixed addresses and patched at runtime | Win64 PE and Linux ELF native game entrypoint into fully compiled game engine with no original PS4 executable loaded, mapped, interpreted, decoded or executed |
| AOT function completeness and translator fallback | `bloodborne-recomp` reports ~96.2% instructions, ~181521/181570 functions but only ~0.5% verified call-by-call and fallback translator still present | Generated-game C/COFF/ELF full call graph and branch semantics closed, remaining functions/imports/exception/setjmp/indirect calls resolved with reproducible behavior validation |
| System imports and libc | `layers/system.md` says PS4 interface translation remains even when original PS4 firmware isn't running | Native Win32/Linux files/threads/TLS/memory/time/input/save/network/audio/video calls with tested semantics and no PS4 syscall dispatch |
| GPU engine-level draw path | `layers/renderer.md` and `layers/gpu-commands.md` explicitly say draw/dispatch still translated from original PS4 packet stream | Replace all graphics paths with authoritative engine-native draw state and compiled material/shader/texture/animation resources; use D3D12/Vulkan directly without PM4/GNM translator |
| Full game offline correctness | Resource parsers and synthetic native GPU renders do not start Bloodborne's actual game | Complete playthrough incl. base/DLC/chalices, NPCs, AI, cutscenes, saving/loading with zero guest runtime; test on actual native Windows/Linux hardware |
| FPS and multiplayer correctness | Original 30Hz ties and distinct online tick model unverified | Instrument/patch source-engine real timers, 60Hz simulation and 30Hz compatibility, offline and multiplayer frame-rate invariance across render caps |

**Next V378:** connect this binary preflight to existing V207/V287/V309 private aggregate evidence **without leaking retail names**, then implement a provenance-checked native call-graph/import closure report. Do not mark strict-native game ready on a synthetic PE/ELF or a passed static scanner; require actual Windows/Linux game startup and long-running offline behavior with guest fallback physically disabled. Simultaneously use authentic original/DS3 timer and HKX tests only privately.

## Current proof scope / security / non-destructive operation

All public fixtures are independently invented C/Python bytes, never original Bloodborne/DS3. Fail closed on unknown imports and corrupt headers, but no static dependency scanner can prove a native binary never dynamically loads a guest executable; runtime file-access traces and code-review are separately required. No production Fornex server writes, user save modifications, deployed launcher updates or automatic merge of stacked draft PRs. Existing V376 skinning, V367 D3D12/V372 Vulkan and BBSC playable guest compatibility branch remain intact.

## Verified cross-platform V377 CI

**PASS, Windows and Linux (2/2):** https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43194377093 . The workflow source commit is `797fc5e79c23128851a8fac86a1a5f19e24fe044`.

Linux ran GCC and Clang C11 frame-clock tests, Clang ASan/UBSan frame-clock tests, Python malformed synthetic PE/ELF preflight and a **real compiled, executed Linux ELF64** analyzed with one reviewed `libc` import. Windows ran clang-cl C11 fixed-clock tests, Python malformed synthetic PE/ELF tests, and a **real compiled, executed Win64 PE32+** with one reviewed import. Both static checks emitted `native_container_verified: true`, **`runtime_no_guest_proven: false`, `whole_game_boot_proven: false`**. These false values are intentional and must not be replaced by optimistic inference.

The fixed-60 clock synthetic test emitted `NATIVE_V377_FIXED60_SIM_30_60_120_240_UNLIMITED_RENDER_CAPS_PASS` across GCC, Clang, Linux sanitizers and Windows clang-cl. No genuine Bloodborne gameplay or graphics frames were used in these tests.
