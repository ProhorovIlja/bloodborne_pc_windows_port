# Native V370 — actual Linux Vulkan FLVER2 indexed draw (offscreen)

Date: **2026-11-12**. Parent branch: `feature/native-v369-vulkan-persistent-staging-20261112`.
Head branch: `feature/native-v370-vulkan-offscreen-flver-draw-20261112`.

## Verification result

**SUCCESS:** https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43170009172

This is the first **rasterized** native Vulkan geometry smoke in our strict no-runtime-EBOOT source-port research path, following the real Windows D3D12 and Linux Vulkan uploads in V365–V369. The test draws triangles from an actual Vulkan device-local buffer produced by the V369 FLVER streaming loader, reads pixels back to the CPU, and asserts actual colored pixels appear exactly where geometry should be.

The Linux GitHub Actions runner installs Vulkan headers/loader, Mesa lavapipe CPU Vulkan driver, glslang-tools and Vulkan validation layers. CI runs native Vulkan Vulkan 1.0, no Proton/Wine/DXVK/guest PS4 code.

**Observed exact pixel counts on lavapipe, 64x64 RGBA8:**

| Invented indexed FLVER2 mesh | Pixel result | Expected |
|---|---:|---|
| Three float3 vertices forming a triangle within the clip volume | **1,094** solid green pixels | Green triangle at frame center; black/opaque corner |
| Identical indexed mesh with all x positions moved +3 outside clip volume | **0** green pixels | Fully black/opaque frame |

The counts and full per-run success markers match across GCC, Clang and Clang ASan+UBSan runs (three executions). No Vulkan Validation Error appeared in inspected job logs. CI contains no original game files, EBOOT/ELF, decrypted binaries, proprietary models, shader binaries or save data.

## Code and reproducibility

1. `native_vulkan_flver_draw_v370.h/.cpp`: a deliberately **narrow** synchronous Vulkan 1.0 offscreen renderer that accepts an already-uploaded `UploadedModelV369` and caller-supplied SPIR-V. It requires **exactly one** three-vertex `float3` position stream (R32G32B32_SFLOAT, stride 12, location 0), **one** R16_UINT index set of three indices, and **one** declared indexed triangle-list draw. All source memory ranges and geometry were validated when V369 created the upload. Callers must verify that V369's upload fence is complete before drawing.
2. The backend creates an optimal-tiled VK_FORMAT_R8G8B8A8_UNORM 64x64 color image with COLOR_ATTACHMENT + TRANSFER_SRC usage, a render pass, framebuffer, vertex/fragment shader modules, graphics pipeline with vertex binding, and a host-visible coherent readback buffer. It records `vkCmdBindVertexBuffers`, `vkCmdBindIndexBuffer`, **`vkCmdDrawIndexed`**, render-pass completion, a COLOR_ATTACHMENT_WRITE→TRANSFER_READ image barrier, `vkCmdCopyImageToBuffer` and a TRANSFER_WRITE→HOST_READ buffer barrier. It waits for a real GPU fence before returning RGBA bytes. Temporary Vulkan resources have explicit cleanup. This test helper **blocks** and is not a frame loop or presentation engine.
3. `native_v370_triangle.vert` and `native_v370_triangle.frag`: independently authored public GLSL, compiled during CI using `glslangValidator -V`. They consume float3 positions and write a solid green fragment. This is **not** Bloodborne's original shader program.
4. `test_native_vulkan_flver_draw_v370.cpp`: constructs two synthetic FLVER2 assets by placing invented float3 coordinate bytes into the already-tested minimal FLVER2 geometry contract. Uses V369's shared 96-byte staging allocator to perform actual GPU uploads of both models before waiting; then submits offscreen draw calls, reads RGBA pixels and asserts a triangle/blank distinction. Negative paths reject malformed SPIR-V magic and unsupported vertex stride. Validated no proprietary bytes.
5. `.github/workflows/native-v370-vulkan-offscreen-draw.yml`: CI builds FLVER validators as C11, GLSL as SPIR-V, renderer/test as C++17 with GCC+Clang, and full sanitized Clang ASan/UBSan. The software Vulkan ICD and validation layer are explicitly selected, not silently substituted by Proton.

Relevant spec behavior: Vulkan render pass requires a color attachment, graphics pipeline and command buffer; an image produced as a color attachment must transition to TRANSFER_SRC_OPTIMAL with appropriate access/stage dependency before `vkCmdCopyImageToBuffer`. See the Khronos Vulkan-Docs Synchronization Examples and Vulkan specification. These rules are encoded in the source, not copied from another project's renderer.

## Critical limitations — do not call this a playable game

- This test draws **invented triangle-list geometry**, not a real Bloodborne FLVER model. Real Bloodborne vertex layouts may use packed position/normal/UV, multiple vertex streams, strips and restart indices, skinning/morphing/cloth, material descriptors, shaders, textures, skeleton transforms and animation. These must be decoded and verified independently. The V370 fixed-test float3 contract MUST NOT be automatically assigned to game assets.
- The rasterized frame is **offscreen**; there is no SDL window, swapchain, depth/stencil path, physical GPU benchmark, HDR, upscaler, frame pacing, shader warmup or in-game presentation yet.
- The helper submits and waits for one draw. It proves correctness in software Vulkan, not 60/120/240 FPS or asynchronous production rendering; adding waits to an actual frame loop would cause stutter.
- The Linux build is a native test executable, **not a complete independent Windows/Linux Bloodborne game**. Full original 1.09 game-function static AOT/import/AI/physics/audio/cinematics/saving closure is still unsolved. In particular the final playable executable must **not** load or interpret PS4 EBOOT/ELF or use PS4 guest ABI/GPU translation at runtime.
- No result here proves online matchmaking, co-op, invaders, dedicated/LAN servers, performance on physical GPUs, DLC, chalices or complete game stability. Save/production server systems were not touched.

## Global GitHub donor research — findings relevant to next milestones

Reviewed source-focused upstreams and PRs beyond our own branch, with explicit constraints:

- [Yharnam-Hunters/Paleblood #655](https://github.com/Yharnam-Hunters/Paleblood/pull/655) **open**, 2026-11-12: identifies hardware tessellation/geometry shader stage enable masks. This is evidence that future native Bloodborne shader mapping must support more than vertex+pixel stages and shouldn't silently render unsupported draw variants as basic triangles.
- [Paleblood #652](https://github.com/Yharnam-Hunters/Paleblood/pull/652) **open**, 2026-11-12: indirect draw packet semantics and `vkCmdDrawIndirect`. This provides a future compatibility checklist, not proof those cases work in our native renderer.
- [Paleblood #611](https://github.com/Yharnam-Hunters/Paleblood/pull/611) **merged**, 2026-11-11: grouped Vulkan work into fewer queue submissions. Revisit when replacing V370's blocking draw with a real async frame scheduler.
- [Paleblood #630](https://github.com/Yharnam-Hunters/Paleblood/pull/630) **merged**, 2026-11-12: deferred presentation/snapshot completion. Revisit for native swapchain pacing; their benchmark does not transfer to our source port.
- [droogie/bbhost #73](https://github.com/droogie/bbhost/pull/73) **open, not merged**: DLSS/FSR upscaling, frame generation, motion vectors and NVIDIA Reflex. Useful candidate for vendor capability/latency test matrices, **not** a ready-to-merge or proven universal performance feature.
- [droogie/bbhost #228](https://github.com/droogie/bbhost/pull/228) merged: shader hot-edit/plugin API and ultrawide temporal reconstruction fixes. Strong future mod/QoL regression checklist; audit per-feature provenance and license before adaptation.
- [soulsmods/SoulsFormatsNEXT](https://github.com/soulsmods/SoulsFormatsNEXT) and [JKAnderson/SoulsFormats](https://github.com/JKAnderson/SoulsFormats): independent real FLVER format and vertex/member descriptions (GPL-3.0 source, no direct code copy). The next tasks must compare actual private-owner Bloodborne meshes, not overfit to this synthetic one.
- [Khronos Vulkan-Docs](https://github.com/KhronosGroup/Vulkan-Docs), [GPUOpen VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator) and [libsdl-org/SDL](https://github.com/libsdl-org/SDL): Vulkan synchronization, device memory management and native cross-platform input/windowing references.

This is a broad targeted scan, not a physically impossible claim to enumerate all public/private repositories, forks, branches and issues on GitHub. Continue repeated subsystem-driven searches. Third-party assets/licenses/revisions require verification before reuse.

## Next implementation milestones

1. **V371: real FLVER vertex semantics** — expose explicit layout member types/semantic/offset/normalization and face topology in a verified format contract for actual owner-private BB/DS3 samples. Decode positions/normals/UVs safely and produce engine-native vertex buffers. Keep all proprietary models private. Reject unsupported layout variants explicitly.
2. **Native Windows D3D12 draw parity** — execute a comparable real indexed draw into a render target using the V367 GPU buffers and readback; verify visible/offscreen pixel counts under WARP. This is crucial to support both Windows and Linux independently.
3. Replace one-shot blocking offscreen draw by a real window/swapchain, render graph, asynchronous frame fences, shader/pipeline caching, material/texture data and safe streaming integration. Measure actual p95/p99 frame times and GPU memory on physical devices.
4. **Parallel critical path:** continue full independent Bloodborne 1.09 game-logic AOT and import closure without runtime interpreter/PS4 ELF. A playable standalone port is not reached by the graphics smoke alone.
5. Preserve V366 ultimate backlog (native KBM/chord/controller remap, custom jump, NG+, input glyphs, DLSS/FSR/XeSS/Reflex where supported, shader warmup, QoL, mod support, LAN/online/dedicated/region selection, performance/crash/pacing metrics) until offline correctness gates allow their implementation.

No Fornex deployment, private game file publication or player save modification. All PRs are kept Draft pending further review and real owner-data validation.
