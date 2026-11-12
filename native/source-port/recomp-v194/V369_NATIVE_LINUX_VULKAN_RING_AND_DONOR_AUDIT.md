# Native V369 — persistent Linux Vulkan staging and ordered fence retirement

Date: 2026-11-12
Base branch: `feature/native-v368-linux-vulkan-flver-20261112`
Head branch: `feature/native-v369-vulkan-persistent-staging-20261112`

## Goal

Develop an independently executable Windows/Linux Bloodborne source port with no original PS4 EBOOT/SELF/ELF, guest CPU interpreter, PS4 kernel/HLE ABI, or PS4 GPU command translation **at runtime**. User-owned CUSA03173 v1.09 and Dark Souls III are permitted offline provenance/research inputs, never redistributed. V369 builds an actual native-Linux GPU resource streaming prerequisite; it is **not** a full native game launch.

## Changes

1. `native_vulkan_flver_stream_v369.{h,cpp}`: new Vulkan 1.0-compatible native Linux FLVER2 multi-resource stream with one persistently mapped HOST_VISIBLE|HOST_COHERENT staging VkBuffer/VkDeviceMemory, one graphics VkQueue and the existing V366 bounded ring scheduler.
2. Models undergo the V362 geometry validation and V364 vertex/index/draw planning. Each model receives a separate DEVICE_LOCAL destination VkBuffer; shared UPLOAD bytes are suballocated at four-byte alignment. Validated model bytes are copied once to mapped staging. Vulkan records `vkCmdCopyBuffer` and a transfer-write to vertex/index-read buffer barrier.
3. A distinct VkFence and VkCommandPool owns each submitted transfer; pending records are retired only when `vkGetFenceStatus` confirms completion **in queue order**, then the shared ring advances. Nonblocking `submit_flver` returns backpressure instead of waiting for GPU capacity. `wait_for(ticket, timeout)` is available to the owning asset worker, not per-file inside the render loop.
4. Source FLVER memory is caller-owned and may be reused after CPU staging. A `std::shared_ptr` keeps each destination VkBuffer/VkDeviceMemory alive even when the user discards the result ticket before GPU completion. Vulkan VkDevice and VkQueue are caller-owned and must outlive the entire stream and all remaining model tickets.
5. Queue submit and device-loss errors fail closed. A stopped/invalid GPU cannot be reinterpreted as a successful fence or an opportunity to overwrite in-flight staging. The destructor may block at shutdown and must not run on a frame-critical thread. The API is not internally multithread-safe; source bytes must remain immutable during submission.

## Tests

File: `test_native_vulkan_flver_stream_v369.cpp`.

CI: **SUCCESS** https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43168436604

- Actual Mesa lavapipe CPU Vulkan physical device, native VkInstance, VkDevice and graphics queue.
- Two synthetic FLVER models accepted and queued using the **same 96-byte staging allocation**, with no wait between submissions. Corresponding DEVICE_LOCAL VkBuffers are read back and compared byte-for-byte.
- Following GPU fence completion and ring retirement, a third different FLVER model reuses staging and its GPU buffer is read back correctly.
- An output ticket is destroyed before its GPU work completes, testing separate in-flight ownership; waiting for its fence succeeds and retires it safely.
- Too-small 40-byte staging budget, invalid triangle indices, empty model and invalid configuration checks.
- GCC and Clang compile/execute native Vulkan, then Clang ASan+UBSan compilation and real Vulkan run.
- All public fixtures are independently invented. Original copyrighted Bloodborne/DS3 assets, EBOOT/ELF and user saves are not in repository or CI.

Initial CI failed because an inline C++ constructor instantiated a container of an incomplete private `Pending` type. Defining the constructor out-of-line after the private type fixed it. Current exact-source V369 CI is green.

## Research and transplant gates

A targeted GitHub review includes these sources; this is **not** a claim to have exhausted every repository/branch/PR on GitHub:

- [Paleblood #595](https://github.com/Yharnam-Hunters/Paleblood/pull/595): ringed Vulkan command batches and timeline-semaphore completion; our Vulkan 1.0 MVP uses per-submission fences for broader device compatibility. Optional timeline path could be negotiated on Vulkan 1.2+ later.
- [Paleblood #611](https://github.com/Yharnam-Hunters/Paleblood/pull/611): merged, batches multiple buffers into one Vulkan queue submission; potential reduction in driver submission overhead for later V370+.
- [Paleblood #630](https://github.com/Yharnam-Hunters/Paleblood/pull/630): merged, presentation snapshot/flip operations deferred to avoid unnecessary waits; relevant only once we implement a real native Vulkan swapchain.
- [bbhost #183](https://github.com/droogie/bbhost/pull/183): merged fix for failed Vulkan memory binding. V369 refuses to publish any output until memory binding, command recording and queue submission succeed.
- [GPUOpen VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator) MIT: candidate for destination allocation pooling, budget-aware residency and lower fragmentation.
- [Khronos Vulkan-Docs](https://github.com/KhronosGroup/Vulkan-Docs): memory coherency/barriers and fence ownership reference. Keep Vulkan validation layers and cross-vendor GPU tests as future gates.
- [SoulsFormatsNEXT](https://github.com/soulsmods/SoulsFormatsNEXT): data-layout donor for later texture/material/shader mapping, **not** a game engine.
- [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp), [Astrr00/BloodbornePC](https://github.com/Astrr00/BloodbornePC): independent code-generation and guest-interpreter-elimination research. Full original game AOT/import closure remains substantially more work than these asset-stage modules.

We do not copy donor source implementations without checking licenses, ownership and independently verifying the behavior. Using Proton, DXVK or VKD3D-Proton as research or optional compatibility tools must never become a required runtime dependency of a true native Linux executable.

## Scope and performance claims

V369 proves CPU→Vulkan GPU resource transfer correctness and fence-safe staging reuse under **software Vulkan lavapipe**. It does not prove frame output, real GPU performance on AMD/NVIDIA/Intel, low frame time, optimized VRAM memory allocations, zero stutter, game-logic boot, shader/texture/animation support, game saves, The Old Hunters progression, online server operation or comprehensive runtime stability. A nonblocking per-file submit still allocates destination resources and command pool/fence objects for each model; actual command batching, destination pooling and timeline semaphore reuse remain optimization tasks.

## Next critical steps

1. Native Vulkan per-batch destination-memory allocation/pools, validation layer coverage, bounded upload queue backpressure and GPU counters. Compare hardware GPU + mesa lavapipe under identical resource fixtures.
2. Cross-platform shader pipeline and **actual triangle draw** from correctly decoded FLVER2 attributes, with a real swapchain/lighting/materials milestone. Do not label verified bytes alone as a visible game.
3. Integrate bounded async disk IO/DCX→BND4→FLVER2 streaming priorities, decompression and cancellation into both V367 Windows and V369 Linux upload schedulers. Shader warmup, pipeline cache keyed to device/build, frame pacing counters and memory-pressure eviction are subsequent gates.
4. In parallel, continue full game-function static AOT/recompilation and Win64/Linux native import closure with zero guest interpreter or ELF loading at runtime. This is the principal blocker for a genuinely playable game.
5. Keep the complete user-requested remaster/control/NG+/mod/online/latency/performance requirements in `V366_PROTON_NATIVE_GPU_RING_AND_ULTIMATE_ROADMAP.md`, implement only after complete offline-game correctness.

No production Fornex or player-save writes, original game file modifications, automatic PR merges or distribution of copyrighted game resources.
