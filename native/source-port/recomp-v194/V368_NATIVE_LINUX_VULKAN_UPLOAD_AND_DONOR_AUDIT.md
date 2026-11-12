# Native V368 — Linux Vulkan FLVER upload and lavapipe verification

Date: 2026-11-12.
Parent branch: `feature/native-v367-d3d12-shared-stream-20261111`
Native feature branch: `feature/native-v368-linux-vulkan-flver-20261112`

## Result

V368 establishes an actual, platform-native Linux **Vulkan** resource-upload route using the same independent FLVER2 geometry validator and source-range planner used by Windows Direct3D12 V365/V367. The resulting Linux executable links to Vulkan directly. It does **not** invoke Proton, Wine, DXVK, VKD3D-Proton, an emulator, a PS4 guest executable or any game-owned PS4 ABI.

The new `native_vulkan_flver_upload_v368.{h,cpp}` accepts a caller-owned FLVER2 asset plus `VkPhysicalDevice`, `VkDevice`, an appropriate graphics queue and graphics queue-family index. It reruns FLVER validation and upload-range planning (V362/V364), refuses over-budget and malformed models, allocates a HOST_VISIBLE + HOST_COHERENT UPLOAD-like Vulkan staging buffer and a DEVICE_LOCAL vertex/index destination buffer, uploads verified source data, records `vkCmdCopyBuffer`, issues transfer-write→vertex/index-input memory barrier, and submits the command buffer to the native Vulkan queue with a fence. The output ticket retains all resources until GPU completion and may be polled or waited with a caller-supplied timeout.

The CPU source model may be released after successful staging. The caller's `VkDevice` must outlive every ticket, and the application must not consume result buffers before successful fence completion. Destruction of an unfinished ticket can block; do not destroy outstanding uploads on the render thread. The current staging buffer is allocated **per asset**, not yet a persistent pooled Vulkan allocator/ring. The code requires host-coherent staging and device-local destination allocation; unsupported memory-type configurations deliberately fail rather than using invalid cache-coherency assumptions.

## Validation evidence

**SUCCESS:** https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43167360115

The workflow `.github/workflows/native-v368-linux-vulkan-flver.yml` runs on Ubuntu 24.04. It installs `libvulkan-dev` and `mesa-vulkan-drivers`, locates the actual Mesa lavapipe Vulkan ICD manifest (which varies by package), compiles FLVER2 C validators with Clang, then builds and runs native C++17 Vulkan transfers with Clang and GCC.

`test_native_vulkan_flver_upload_v368.cpp` selects a CPU Vulkan physical device (Mesa lavapipe), creates a real Vulkan instance/device/graphics queue, submits two distinct synthetic FLVER models, and checks that each 42-byte vertex/index GPU destination matches the invented source data after command submission, proper Vulkan memory barriers and readback to host-visible memory. It tests under-budget rejection, malformed FLVER index rejection and an empty mesh. It also performs a sanitizer-compiled and executed Vulkan readback with ASan+UBSan. No user-owned game assets enter public CI.

An initial workflow run stopped before compilation because it expected a particular lavapipe ICD filename. The follow-up workflow discovered the installed manifest instead and passed all jobs. The final run is cited above. The initial failure does not imply a Vulkan source-code failure.

This is a **software Vulkan GPU-correctness test**, not a benchmark on NVIDIA/AMD/Intel hardware. No physical GPU fps, stutter, shader compile time, or end-to-end game performance claim follows.

## New GitHub donor/PR review

Scanned relevant additional projects and upstream PRs. Findings are research inputs, **not silently merged code**:

- [GPUOpen VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator) (MIT): candidate for production device-memory pools, suballocation and budget handling. V368 deliberately starts with explicit dedicated VkDeviceMemory for testability, then should use a pooling abstraction.
- [Khronos Vulkan-Docs](https://github.com/KhronosGroup/Vulkan-Docs): primary rules for memory-type/host-coherency selection, barrier scopes, buffer usage and fence lifetimes.
- [Paleblood #611](https://github.com/Yharnam-Hunters/Paleblood/pull/611) (merged 2026-11-11): multiple Vulkan command buffers grouped into fewer queue submissions. Reported fewer submissions and waits in the author's Contract-screen case. Adapt batching carefully to our **native asset** queue rather than imitating its PS4 memory model.
- [Paleblood #630](https://github.com/Yharnam-Hunters/Paleblood/pull/630) (merged 2026-11-12): flips no longer stall waiting for subsequent GPU work; completion-thread snapshot and batched command recording reduce per-frame idle time. Relevant once our native swapchain and presentation path exist.
- [Paleblood #595](https://github.com/Yharnam-Hunters/Paleblood/pull/595): ringed Vulkan submissions and timeline-semaphore tickets motivate a future V369 Vulkan stream owning one host-visible staging heap, one queue and a timeline semaphore.
- [bbhost #183](https://github.com/droogie/bbhost/pull/183): ensure failure to bind Vulkan memory never publishes an unusable resource. V368 publishes an upload only when buffer creation, memory allocation/binding, command recording and queue submit succeed.
- [SoulsFormatsNEXT #53](https://github.com/soulsmods/SoulsFormatsNEXT/pull/53) (merged): shader metadata analysis, useful for future native FLVER material/shader mapping, not an implementation of Bloodborne's renderer.
- [Microsoft DirectStorage](https://github.com/microsoft/DirectStorage): possible Windows-only future file IO backend; native Linux needs its own async IO path.

No third-party implementation is copied, no incompatible runtime bundled. Per-file license checks are required before any future reuse. The research is broad but not an impossible claim to have inspected every repo, issue, branch or private source on GitHub.

## Core native-port invariant and requirements

The independent final Windows/Linux game must load and execute **no original PS4 EBOOT/SELF/ELF or translated guest instructions at runtime**. The owner can provide their own game as offline source/reconstruction material; proprietary game bytes are never published.

The long-term backlog, including Windows/Linux native builds, player-owned mod support, key/chord and gamepad remapping, independent jump input, scalable HUD glyphs, manual NG+, co-op/invasions/dedicated or LAN servers, netcode metrics, region selection, shader warmup, HDR/VRR and selectable DLSS/XeSS/FSR/Reflex, is retained in `V366_PROTON_NATIVE_GPU_RING_AND_ULTIMATE_ROADMAP.md`. Proton/DXVK/VKD3D-Proton remain optional compatibility comparison and donor research, not native Linux requirements.

Neither V368 nor its predecessors yet proves game startup, a shader pipeline, a rendered FLVER model, material decoding, animation, offline playthrough or online stability. Those need separate tests, data provenance checks and measurable acceptance criteria.

## Next steps

1. Implement native Vulkan persistent staging and resource-lifetime ring, using V366/V367 ownership lessons, correct queue timeline synchronization and memory suballocation; test against lavapipe plus physical GPUs.
2. Build a minimal cross-platform shader/material/mesh draw smoke, not just buffer readback. Ensure vertex input layout reflects real FLVER2 layout semantics and shader metadata.
3. Add priority/cancellation-aware asset reads and decompression to the DCX→BND4→FLVER2 pipeline and integrate both native render backends; measure VRAM/CPU memory pressure and shader warmup time.
4. Advance the **independent original 1.09 game AOT/import closure** work in parallel, with an automated report of unresolved guest-interpreter or PS4 ABI dependencies. This remains the main blocker for a standalone native Bloodborne executable.
5. Only after consistent complete offline gameplay: implement the remaster-quality controls, QoL, online, performance and latency options described in V366.

No deployment, no live Fornex/service modifications, no original private game files, no user-save changes and no automatic merge of staged draft PRs.
