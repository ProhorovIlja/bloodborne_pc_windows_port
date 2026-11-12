# Native V373 — Windows Direct3D 12 indexed packed FLVER draw and WARP readback

Date: 2026-11-12
Base: \`feature/native-v372-flver-packed-vulkan-draw-20261112\`
Head: \`feature/native-v373-d3d12-packed-flver-warp-draw-20261112\`

## Verified result

V373 closes the first **native GPU draw parity** milestone between our Windows Direct3D 12 and Linux Vulkan asset pipelines, without using PS4 executables, guest CPU JIT/interpreter, PS4 GPU packet translation, HLE, Wine or Proton.

**GREEN on the source commit**: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43176085540

On Microsoft software WARP in Windows Server 2022 runner, the test:
- Creates a native DXGI WARP adapter, Direct3D 12 device and DIRECT queue.
- Instantiates the existing V367 **persistent shared staging/fence** FLVER2 uploader. It submits two independently invented FLVER2 models before waiting on a GPU fence.
- For the **44-byte-per-vertex packed layout** independently verified against owner-private Bloodborne/DS3 samples in V371, the actual GPU vertex/index buffer is bound directly to a D3D12 graphics pipeline whose position input is R32G32B32_FLOAT at byte offset 0. Calls \`DrawIndexedInstanced(3,1,0,0,0)\`, renders into 64×64 RGBA8, transitions to copy-source, copies to a READBACK resource, synchronizes on a GPU fence, and checks pixels: **1,094 green pixels** in visible triangle.
- For a **36-byte-per-vertex packed layout** also described in owner samples, moves invented triangle outside clip space; WARP returned **0 green pixels** and a black frame.
- Uses **row-pitch-aligned texture readback** from \`GetCopyableFootprints\`. Does not assume tightly packed texture rows; flattens 64x64 pixels after fence completion.
- Rechecks V362/V364 complete FLVER and upload ranges, V371 supported vertex semantics, float3 position/finite coordinates, source/gpu metadata identity, triangle-list topology and 16-bit indices. Rejects malformed normal type, forged GPU vertex stride, triangle-strip and NaN coordinate without invoking D3D12.
- Runs \`native_flver2_vertex_decode_v371\` synthetic unit tests on Ubuntu24 GCC/Clang/ASan+UBSan separately, keeping data-only safety contracts covered in Linux as well as Windows. **Both CI jobs passed.**

The same invented 44-byte triangle renders 1,094 green pixels with our Vulkan/lavapipe V372 path; this is a useful cross-API correctness comparison for this exact simple triangle, not evidence of identical shader/quality/latency performance for real game geometry or physical GPU vendors.

## Authored files

- \`native_d3d12_flver_draw_v373.h/.cpp\`: **independently authored** Win64 D3D12 offscreen smoke. Uses root signature/graphics PSO, HLSL Shader Model 5.1 diagnostic shaders compiled at test runtime with \`D3DCompile\`, one RTV render target, indexed draw, GPU texture-to-buffer readback. No original Bloodborne shaders or images.
- \`test_native_d3d12_flver_draw_v373.cpp\`: two invented models with exactly the tested V371 44-byte/36-byte member semantics and three indices, expected WARP pixel counts, malformed source and draw negatives.
- \`.github/workflows/native-v373-d3d12-packed-flver-warp-draw.yml\`: builds with clang-cl (C11 validator objects, C++17 D3D12 test linked with official Windows SDK libraries). Windows WARP tests **real indexed GPU rendering**; Linux GCC/Clang/ASan/UBSan keep independent C decoder regression tests. No private game assets in public CI.

## Scope and safety boundaries

- The test proves native D3D12 indexed drawing and pixel readback **for invented FLVER2 records using types observed in private genuine game data**. It does NOT render an actual whole BB character, boss, Central Yharnam environment, The Old Hunters DLC, real textures, bone-skinned vertices, animation, material shaders, alpha sorting, HDR, depth testing or higher-count face sets.
- The graphics helper is **synchronous**, intentionally blocks until a GPU fence completes, creates fresh graphics pipeline/targets per call and embeds a simple invented green shader. Do NOT use it directly inside a production frame loop. Frame pacing, asynchronous pipeline compilation, GPU resource pooling and shader caching still need implementation.
- The caller must wait for V367 upload completion and ensure source FLVER bytes are the same immutable bytes used for upload. V373 checks layout metadata and a CPU validation preflight but does **not** cryptographically attest source-to-GPU contents; provenance/generation tags must be implemented before untrusted mod data is accepted.
- The diagnostic helper is not a robust device-lost recovery engine. Any queue Signal failure or invalidated D3D12 device mandates tearing down the renderer; future production engine must have explicit error-state and teardown ownership, and structured GPU device-removal tests.
- Render state and D3D12 queue are assumed to be caller-owned. No promise is made about actual NVIDIA/AMD/Intel GPU support or FPS without real-hardware testing.
- This is not a native Bloodborne executable or proof of AOT/import closure. The original 1.09 game logic, cutscenes, audio, gameplay, saves, DLC, network and online systems are not running in this renderer smoke.

## Additional GitHub and public donor review (2026-11-12)

Research is broad and ongoing, **not** a false assertion of an exhaustive crawl of every GitHub repository, fork, branch or PR.

- [bloodborne-native/bloodborne-recomp/docs/RECOMPILATION.md](https://github.com/bloodborne-native/bloodborne-recomp/blob/main/docs/RECOMPILATION.md): important **whole-game AOT evidence**. The published 2026-11-02 table describes 179,698 original executable functions, ~10.7M instructions, ~96.2% of instructions recompiling, and translator fallbacks remaining for some imports and \`setjmp\`/patchable paths. Call-by-call verification coverage remains small. Investigate its deterministic record/replay methodology, import closure, and compiler flag/memory ordering correctness. Crucial: **their game still permits original-code translator fallback**, so this is NOT a complete strict no-guest-executable source port. The project targets native ARM/macOS and needs porting/ABI research for Win64/Linux.
- [SoulsFormatsNEXT #56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56), merged: consume FLVER data without instantiating every per-vertex object; aligns with our direct GPU packed layout validation idea but no code copied.
- [Paleblood #655](https://github.com/Yharnam-Hunters/Paleblood/pull/655), merged: observe and gate extra shader stages including tessellation/geometry; do not silently reinterpret complex materials as normal triangle-list draws.
- [Paleblood #652](https://github.com/Yharnam-Hunters/Paleblood/pull/652), **merged by 2026-11-12**: indirect draw packet semantics. Future native renderer must decode source-engine draw behavior rather than hardcode one \`DrawIndexed\` path.
- [Paleblood #611](https://github.com/Yharnam-Hunters/Paleblood/pull/611), merged: GPU command batching lessons relevant to future low-CPU-overhead upload/present.
- [droogie/bbhost #228](https://github.com/droogie/bbhost/pull/228), merged: shader plugin/FX test and ultrawide temporal reconstruction bug fixes. Relevant only after authentic native BB shader/material pipeline.
- [droogie/bbhost #73](https://github.com/droogie/bbhost/pull/73), **still open**: DLSS/FSR/Reflex upscalers/frame-generation design and capability fallbacks; this is **not** an already-integrated feature in our source-native renderer.
- [microsoft/DirectX-Graphics-Samples](https://github.com/microsoft/DirectX-Graphics-Samples), [KhronosGroup/Vulkan-Docs](https://github.com/KhronosGroup/Vulkan-Docs), [GPUOpen D3D12MemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator), [VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator), [ValveSoftware/Proton](https://github.com/ValveSoftware/Proton), [doitsujin/dxvk](https://github.com/doitsujin/dxvk), [HansKristian-Work/vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton): validate graphics API/sync/memory budgets, optional compatibility routes and pipelines, while preserving completely independent native Windows/Linux execution.

Review donor licenses and actual code/benchmark evidence before importing. A PR description is a hypothesis until reproduced.

## Next engineering stage

**V374** should attempt a real owner-private BB model **mesh/face topology inspection** with no copyrighted bytes published: identify drawable bind-pose vertices, genuine index arrays, mesh transformations/bone matrices and draw ranges. Then introduce *multi-triangle draw batches* on both native render backends and visual comparison to original-game screenshots using owner's own local assets. Do not claim full skinning without actual bone hierarchy and skin matrices.

Simultaneously continue the **most important blocker**: complete independent BB 1.09 game-function static AOT/native OS import closure with an automated list of unresolved functions/guest-runtime dependencies. The final Windows/Linux native executable must load **no** original PS4 EBOOT/SELF/ELF and use no PS4 CPU/GPU interpreter at runtime. Its assets remain legally user-provided.

After verified complete offline playthrough including DLC and chalices, implement input/key+chord mapping, dedicated jump, controller/UI prompts, NG+ QoL, shader warmup, frame pacing, VRR/HDR and DLSS/FSR/XeSS/Reflex capability integrations, full LAN/self-host/dedicated online and invite/region/netcode metrics from V366's user backlog. No zero-network-latency claim is physically valid.

**No changes to production Fornex services, game files, saves, playable BBPort, Ultimate Yharnam Together, or public distribution of game content. Do not auto-merge Draft branches.**
