# Native V367 — Persistent Windows D3D12 FLVER streaming

Date: 2026-11-11
Base: `feature/native-v366-fence-ring-proton-research-20261111`
Branch: `feature/native-v367-d3d12-shared-stream-20261111`

## Result

The V365 one-resource, one-UPLOAD-heap, one-fence implementation and V366 isolated staging ring are now connected into a **reusable production-shaped Windows-native FLVER resource streaming component**. `D3D12FlverStreamV367` accepts caller-owned validated FLVER model bytes, uses V362 and V364 to build vertex/index/draw plans, copies the source bytes into one persistent mapped D3D12 UPLOAD buffer, creates a separate GPU DEFAULT resource for each accepted model, submits real D3D12 commands to a single DIRECT queue, and signals an incrementing shared fence. No per-resource wait occurs inside `submit_flver`; if upload staging is full it returns backpressure, not a synchronous wait.

Temporary command allocators, lists and references to DEFAULT resources are held per submission and released on actual fence retirement; caller retains a `UploadedModelV367` to use GPU views after `is_complete`. Data from owner-provided source FLVER can be recycled after successful CPU staging. Unsupported formats and memory budgets fail closed. The scheduler is intentionally single-thread-owned; application threads must marshal model submissions to its owning render/asset thread.

This is a CPU/GPUs asset pipeline milestone, **not a standalone Bloodborne game, 3D scene renderer, full-game AOT, offline gameplay or native Linux Vulkan implementation**.

## Actual files

- `native_d3d12_flver_stream_v367.h/.cpp`: persistent UPLOAD heap and global fence, one ring, real D3D12 UPLOAD-to-DEFAULT copies and state transitions, nonblocking submit, explicit completion/poll/wait API, GPU object lifecycle.
- `test_native_d3d12_flver_stream_v367.cpp`: synthetic FLVER2 models with different invented vertex payloads, two submissions before waiting, GPU readback for both, a third submission after safe staging reuse, invalid-model refusal and zero-geometry handling.
- `.github/workflows/native-v367-d3d12-flver-stream.yml`: Windows clang-cl and Microsoft WARP actual GPU transfer test. Linux GCC/Clang plus ASan/UBSan reruns the 50,000-scenario portable V366 ring tests.

CI: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43084313370 — **both Windows and Linux jobs passed**.

### Verified scope and limits

- GPU copying is real Direct3D 12 on **Microsoft WARP** in the Windows GitHub runner, and byte-level GPU readback passed. It does NOT establish physical AMD/NVIDIA/Intel performance, VRAM load, frame pacing, draw-call correctness, animation, shaders, texture/material handling or scene visibility.
- No file-system reads, original Bloodborne/DS3 assets, PS4 ELF/EBOOT, save files, credentials, or live-server access in CI.
- The shared UPLOAD heap remains mapped until stream shutdown. Per-upload DEFAULT buffer is still individually allocated (for now) and per-upload command allocator/list is created (for now); stream does not yet batch multiple models into one command list. A future explicit GPU memory allocator and queue batching are still warranted.
- `submit_flver` is intentionally nonblocking and uses caller-observed backpressure; do not issue blocking `wait_for` on the render loop. The destructor waits for remaining fence-backed work. A failed queue Signal after an Execute is treated as fatal and must lead to renderer/device teardown, not recovery by prematurely reusing bytes.
- State tracking assumes all operations use the same DIRECT queue and no other thread mutates the GPU outputs before the owning renderer acknowledges completion. Never publish a model as draw-ready before `is_complete(fence)` succeeds.
- V364 models are revalidated on every submission. A successful CPU/GPU byte-transfer is NOT equivalent to a verified shader/input layout interpretation or skeletal animation.

## Cross-GitHub donor checks

Verified on GitHub (not blindly copied):
- [Paleblood PR #595](https://github.com/Yharnam-Hunters/Paleblood/pull/595) merged 2026-11-11. Four-slot timeline-semaphore executor and deferred GPU completion avoids per-step waits; suggests shared queues/fence retirement, but its Vulkan/guest-memory semantics do not directly substitute for this D3D12 native source port.
- [bbhost PR #183](https://github.com/droogie/bbhost/pull/183) merged, from closed unmerged #170. A Vulkan staging pool previously published an unbound buffer when `vkBindBufferMemory` failed. We similarly publish no GPU output before successful memory allocation, command closure, execution and fence Signal, and preserve pending resource references until completion.
- [bbhost PR #204](https://github.com/droogie/bbhost/pull/204) merged 2026-11-04. Upload heap waits, GPU memory-pressure and graphics artifact fixes are useful cases for future profiling; performance claims cannot be transferred to our renderer without benchmarks.
- [microsoft/DirectStorage](https://github.com/microsoft/DirectStorage): potential opt-in native Windows asset-read/decompression backend; pair with portable IO abstraction and fallback on unsupported OS/storage. DirectStorage is **not** itself a native Linux solution.
- [GPUOpen D3D12MemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator) (MIT) and [GPUOpen VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator): candidate allocators for explicit residency, real-VRAM budgets and placed buffer pools.
- Proton, DXVK, VKD3D-Proton, gamescope, SDL3 and SDK-based FSR/DLSS/XeSS/Reflex remain documented in the V366 ultimate requirements. They can inform the build/driver design, **not become compulsory runtime dependencies** for native Windows/Linux builds.
- [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp), [Astrr00/BloodbornePC](https://github.com/Astrr00/BloodbornePC), [Yharnam-Hunters/Paleblood](https://github.com/Yharnam-Hunters/Paleblood) remain high priority for independently validated game logic and AOT closure; the full no-runtime-guest-code executable is not solved by V367.

No claim of exhaustive inspection of all GitHub repositories, forks, branches, PRs and internet sources: searches are scoped, repeatable and broadened per subsystem; any imported code must pass per-file license and provenance checks.

## Next critical engineering stage

1. Build a Vulkan counterpart for **native Linux**, with VMA or explicit device-memory allocation, transfer queue, timeline semaphore/fence, and real lavapipe plus physical GPU test. Keep a direct Linux executable; Proton is optional testing only.
2. Add D3D12 destination buffer pooling with resource-release/aliasing rules and queue batching, then measure CPU/GPU frame-time, 4 GiB/integrated GPU memory pressure and long-session leaks on real hardware. Validate device-loss and failed queue Signal paths with fault injection.
3. Connect async file IO + DCX/BND4 FLVER + resource scheduler with cancellation, priority and bounded memory so assets stream while walking between areas; maintain immutable resource source and provenance.
4. Build the actual minimal shader, input layout, render targets and triangle draw smoke using independently decoded FLVER attributes, then materials/textures/animation/physics and full offline play.
5. Continue full game-function AOT plus import closure in parallel. The target remains independent Windows/Linux game executables with **no EBOOT/ELF/PS4 guest runtime**; only after offline correctness, activate networking, remaster-grade settings, QoL and enhancement features.

No Fornex/server writes, no player-save changes, no modification of original game files, and no automatic merge of existing draft PRs.
