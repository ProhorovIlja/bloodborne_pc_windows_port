# PC-first Bloodborne for Windows: native execution contract (V153)

**Status:** experimental and not a full PS4-free recompilation. No PS4 hardware, Sony OS or general-purpose emulator is required to execute the original x86-64 Bloodborne game code in `bbport`. But its ABI, game file formats and GPU commands are from the PS4 edition. We cannot honestly remove all of those by only replacing a few runtime functions. A wholly independent game engine would require comprehensive, legally appropriate reimplementation of proprietary game logic; this project should not risk a playable native runtime by conflating the two goals.

## Actual source-based boundaries (YT 1.3 original, SHA 0645740a)

| Part | Current implementation | PC-native end-state | Evidence / release gate |
|---|---|---|---|
| Game CPU | Original Bloodborne x86-64 guest code in memory from `bbport/scripts/prepare.py`; no CPU interpreter | Native Windows process, safely linked original code or independently reimplemented logic | Clean local 1.09 `eboot.bin`, 2h+ playthrough and native boot coverage |
| Guest imports/ABI | `bbport/src/runtime*.c` respond to original game imports; SysV ABI, Sony NID names are the linkage contract | Windows host APIs behind private, well-tested ABI adapters, gradually remove redundant FreeBSD/PS4 service behavior | Exact original-source staging, real Windows C/C++ runtime tests, failed-import census from V147 |
| Threads/memory | `runtime_thread.c`: guest TLS/TCB on Windows TEB slots. `runtime_memory.c`: Win32 VirtualAlloc2/MapViewOfFile3 placeholders and low address constraints | Windows-native timing, memory, synchronization, thread scheduling with correct game pointers | Memory layout aliasing, GPU page faults, and save-continuation tests; no arbitrary removal of guest 40-bit assumptions |
| Time | Original `runtime_time.c` used CRT/POSIX `gettimeofday()` in Windows `_WIN32` branch | **V153 candidate:** direct `GetSystemTimePreciseAsFileTime()` and Windows timezone/DST; preserve original guest structure | Source-blob pin, original Windows C compilation and 1,024-call live system clock test; full Protocol8 Windows build; performance comparisons before claiming improvement |
| Graphics | Proprietary console GNM/GCN work from the game, converted to Vulkan; forked Vulkan renderer | Direct performant Vulkan renderer, offline and persistent pipeline cache, native swapchain/frame pacing, DLSS/FSR options | Shader correctness on AMD/NVIDIA/Intel, GPU driver/device-loss, cold/warm caches, p95/p99 frames, 2h VRAM/RSS trend |
| Input | `runtime_pad.c` already reads SDL3 gamepads/mouse/keyboard | Native controllers incl. hotplug/rumble/layout, keyboard/mouse rebinding, accessible UI | Controller layouts, simultaneous input, reconnect/alt-tab, real save/reload |
| Audio | `runtime_audio.c` already maps game output to SDL3 audio, with rate correction | Low-latency native Windows audio path, device changes, no periodic crackle | Device disconnect/reconnect, 2h click/underrun stats, 5-player gameplay audio |
| Files and saves | `runtime_file.c` maps `/app0` etc. to Windows disk; `runtime_savedata.c` stores PC-host files with some atomic replacement | Isolated PC save/profile layout, version/migration handling, transactional writes and safe backup/rollback | Never overwrite existing saves; load/continue/travel/exit/restart and crash recovery |
| Online / network | Native network sockets wrapped behind game-import shims; authenticated YT Protocol8 server+client; separate standalone `BB_PARTY` protocol exists in other forks | Native Windows Winsock transport for server-negotiated sessions, encrypted direct P2P game packets, server-only authority/routing/rewards, fallback relay | 5-seat group, invasions, DBNO HUD, consent/key expiry, LAN/WAN/CGNAT, cross-shard invites, 200 players >=99% steady QoS; NO release while previous stress RED |
| Launcher | V146/V147/V148/V149/V152 staged original Protocol8 launcher and binaries, metadata-only input checks | Single native Windows launcher and updater, safe game/region/mod/save detection, signed packages and rollback | Native startup smoke + real game assets and full dependency closure, Windows Defender trust, fresh install/update/uninstall |

## We mean “native PC”, not “zero PS4-shaped bytes”

1. **No emulator, Sony firmware, PS4 virtual machine or PlayStation account dependency** is a realistic PC release goal. Original game's x86-64 instructions are executed directly. The game should use Win32 APIs, Vulkan and native networking through thin adapters with progressively fewer console-specific assumptions.
2. **Zero PS4 ABI, PS4-origin game assets, proprietary GNM/GCN shader formats or original PS4 game code** is a different goal: writing a new game engine/renderer/assets path with gameplay-parity reconstruction. It cannot be achieved merely by switching toolchains, removing `sce` function names or bundling another native runtime. Such a reimplementation cannot be represented as finished without whole-game equivalence testing and appropriate rights.
3. Keep original offline and source-backed playable builds as a rollback baseline. Migrate one subsystem at a time behind strict contracts, not a wholesale deadinside/Mrsuss/bbhost/Lantern/Visy source collage. Preserve licensing and verify exact pinned upstream file/commit.
4. Do not automatically publish proprietary game files or secrets in GitHub Actions artifacts, the public repo, Discord or cloud downloads. User-owned assets remain private; synthetic tests and aggregate inventories are sufficient for source CI.
5. Native Windows transport **must not** silently enable the unrelated standalone `BB_PARTY` wire protocol as if it were the authenticated five-player YT game client. The V148 guard is intentional until original Protocol8 native launch is actually integrated.

## Native migration development gates

**A. Native system-service proof:** on Windows CLANG64, compile the actual YT 1.3 runtime source and execute real OS-backed C ABI tests. Include clock, memory, filesystem, TLS, audio, input and failure returns. A source diff without runtime tests is not considered integrated.

**B. Real Windows game executable:** combine service backports with original YT Protocol8 game, actual Vulkan translation and current GPU fixes in the same build, verify linked `bb-probe.exe` and dependency DLL closure. A linked file is not necessarily playable.

**C. Real-game input parity:** with lawfully supplied game files and no PS4 firmware, cold boot, Dream, save/continue, region/patch version and DLC on at least AMD and NVIDIA; measure 30/60+ FPS, p95/p99 frametime, CPU vs GPU limitation and 2h memory/VRAM. Preserve all saves and allow rollback.

**D. End-to-end online:** direct peer-to-peer only with authenticated server grants and verified encrypted per-peer identity; server mandatory callbacks stay central. Validate two Windows machines, five players, invader mixtures, DBNO, reconnect and CGNAT fallback; run unchanged 200-player QoS threshold and investigate red invite + packet delivery.

**E. Player-facing release:** no incomplete source-only “release”, no Fornex switchover before safe migration rehearsal and public installation/update rollback tests.

## External sources reviewed (candidate value only)

- `deadinside28/bloodborne_pc` v0.7: direct game CPU execution, Win32/Linux single-game runtime, Vulkan GPU translator, record/replay test candidate.
- `droogie/bbhost`: alternate native loader and command processor, CPU/GPU pipeline profiling, own guarded performance experiments. Its FPS numbers are not our measured performance.
- `Mrsuss60/bloodborne_pc_windows_port` / `Supermedo/bloodborne_pc`: native Windows packaging and broad hardware support; adapt independently audited fixes.
- `Awakenchan/LanternEngine` / `visy/bloodborne_pc_windows_port`: native Windows UX, optimization, standalone party and controls; **different multiplayer backend**.
- `lKaniel/bloodborne-server`: authoritative Yharnam Together Protocol8 gameplay, five-seat server experimentation, world progression and co-op requirements.
- `shadps4-emu/shadPS4`: graphics translator correctness and C++ fixes only, never introduce PS4 CPU emulation into our runtime.

**Provenance caution:** this is a living engineering plan based on source inspection; only separately successful CI and gameplay logs establish what is actually working.
