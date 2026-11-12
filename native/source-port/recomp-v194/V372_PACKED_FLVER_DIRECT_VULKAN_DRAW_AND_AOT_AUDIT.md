# Native V372 — Verified packed FLVER2 Vulkan indexed drawing

Date: **2026-11-12**. Parent: \`feature/native-v371-flver-real-vertex-semantics-20261112\`. Head: \`feature/native-v372-flver-packed-vulkan-draw-20261112\`.

## Goal and verified result

Bridge the independently verified V371 Bloodborne/Dark Souls III FLVER2 vertex-member layouts to **actual native Linux Vulkan indexed rasterization** without CPU repacking every vertex into an extra float3-only buffer. Preserve the strict target: independently built Windows and Linux executables with **no runtime PS4 EBOOT/SELF/ELF, guest CPU interpreter, PS4 HLE kernel or PS4 graphics-command translation**. Proton/DXVK/VKD3D-Proton remain optional compatibility/research tools, not requirements.

**PASS packed draw:** https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43174090826

**PASS final regression including original V370 compatibility:** https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43174630372

On Ubuntu 24.04 with Mesa lavapipe, Vulkan validation layers and native GLSL→SPIR-V, each of GCC, Clang and Clang ASan/UBSan ran:
- One invented FLVER2 **44-byte-per-vertex** skinned-attribute layout: raw GPU V369 staging→indexed Vulkan pipeline directly binding position as \`VK_FORMAT_R32G32B32_SFLOAT\` at **offset 0, stride 44**. Visible diagnostic triangle generated **1,094 green pixels** in an offscreen 64×64 image.
- One invented FLVER2 **36-byte-per-vertex** unskinned-attribute layout: direct GPU position fetch at **offset 0, stride 36**. The identical triangle translated outside clip space generated **0 green pixels** and a black frame.
- No runtime CPU vertex repacking or a second GPU vertex buffer for these two outputs. Each still performs source-layout validation and small canonical CPU decode as a **correctness preflight**.
- Negative regressions refuse invalid SPIR-V, a forged GPU metadata stride, a source record whose normal type is changed to an unsupported same-byte-width encoding, triangle-strip topology passed off as triangle-list and a NaN position. The original V370 12-byte API remains strict and rejects the 44-byte model.

The actual rendering is in \`vkCmdDrawIndexed\`, not merely bytes copied to a VkBuffer. GPU output is copied back and exact pixel assertions run on the real Vulkan software device. No physical AMD/NVIDIA/Intel frame-time or FPS improvement is claimed.

## Code

- \`native_vulkan_flver_draw_v370.{h,cpp}\`: a small, backwards-compatible refactor retaining the original strict float3 stride12 public draw function. An explicitly named V372 stride-aware core now takes the validated input stride and binds it to Vulkan's vertex-input descriptor; bounds checking uses \`3 * stride\` instead of a hard-coded 36 bytes. The legacy V370 call still forwards with stride12.
- \`native_vulkan_flver_semantic_draw_v372.{h,cpp}\`: new fail-closed bridge from **immutable original FLVER source + actual V369 uploaded model metadata**. Re-runs V362 full geometry verification via V364, checks that exactly one mesh/face-set/vertex-buffer is referenced, three R16 triangle-list indices, three vertices and exact source/validated GPU sizes. Calls V371 on the original layout and preflights all float positions, verifies Float3 position semantic at offset 0, and accepts only the 12-, 36- and 44-byte member combinations V371 already understands. Checks GPU offsets, strides, counts, face reference, material and draw metadata. Only then invokes the V370 Vulkan draw core.
- \`test_native_vulkan_flver_semantic_draw_v372.cpp\`: only invented public-model bytes, with the **same type/semantic/offset sequence** observed in two private owner-owned original games. One 44-byte test carries normals, tangents, four bone indices, weights, vertex color and signed16 UV pair. One 36-byte test has no bone indices/weights. GLSL uses position only; the other attributes are verified but not yet consumed by shaders.
- \`.github/workflows/native-v372-flver-packed-vulkan-draw.yml\`: Ubuntu Vulkan loader + Mesa lavapipe + glslang + validation layers. C11 V362/V364/V371 validation built with Clang; C++17 V369/V370/V372 GPU paths built with GCC and Clang, plus sanitized C and C++ test. No private copyrighted data in CI.

## User-owned original asset parity, and what it proves

In V371 (separately, **outside public CI**), the same V371 decoder was validated against private CUSA03173 Bloodborne and DS3 PC samples: BB active 44-byte buffer **5,825 vertices**, DS3 four active 44-byte buffers **11,875 vertices** total. Both contain an additional 36-byte layout descriptor. The test in this PR uses **invented positions/indices/material bytes** encoded into corresponding layouts. It does **not** render those original game models, prove a fully valid private Bloodborne skeleton, or include any copyrighted FLVER data.

This V372 helper intentionally restricts drawing to one triangle list with one mesh/face set and 3 indices/vertices. Real character and map geometry requires arbitrary mesh counts, primitive restart/triangle strips, index widths, LOD selection, multiple vertex streams, transforms, skinning/animation and authentic material/shader pipelines. In particular an optional 36-byte layout descriptor does **not** establish that every asset uses it as an active vertex buffer.

### Source-to-GPU provenance limitation

The wrapper compares immutable source layouts and V369 upload **metadata**, but cannot cryptographically prove that the bytes in the GPU upload were produced from exactly that same source after a caller replaces it. The caller must retain the original immutable source used for upload until the draw validation completes; a production asset manager should attach a verified asset/content digest or a generation-tagged authenticated upload ticket, and avoid repeatedly validating whole files on the render thread. The test's negative-source mutations check semantic refusal, not security-grade GPU contents attestation.

V370/V372 offscreen renderer blocks on a GPU fence and creates fresh render resources per call. It is a diagnostic test only; do **not** place it in a production per-frame render loop. Render-state/device-loss and hardware GPU performance require dedicated tests.

## Wider GitHub and upstream audit (not a claim of exhaustive GitHub indexing)

Relevant upstreams reviewed and their status as of 2026-11-12:
- [SoulsFormatsNEXT #55](https://github.com/soulsmods/SoulsFormatsNEXT/pull/55), **merged**: multiple position/normal attributes matter for cloth and alternate geometry. Our V371 strict layout decoder deliberately refuses unsupported repeats instead of guessing; a future expansion needs explicit semantic-index handling.
- [SoulsFormatsNEXT #56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56), **merged**: reading FLVER2 structure without materializing every \`Vertex\` supports direct GPU buffer upload. V372 uses the same architectural idea independently; no upstream code was copied.
- [JKAnderson/SoulsFormats](https://github.com/JKAnderson/SoulsFormats) FLVER LayoutMember and Vertex/FaceSet format semantics: reference for type identifiers, offset and normalization. Third-party licenses/provenance reviewed before any import; our C code is independently authored.
- [Paleblood #655](https://github.com/Yharnam-Hunters/Paleblood/pull/655), **merged**: hardware tessellation/geometry stage masks. Full native Bloodborne render cannot silently interpret every shader variant as an ordinary vertex + pixel pipeline.
- [Paleblood #652](https://github.com/Yharnam-Hunters/Paleblood/pull/652), **open**: indirect draw semantics, important for future draw-path coverage and validation.
- [Paleblood #611](https://github.com/Yharnam-Hunters/Paleblood/pull/611), **merged**: batched Vulkan submission patterns relevant to replacing blocking offscreen smoke with asynchronous rendering.
- [bloodborne-native/bloodborne-recomp — RECOMPILATION.md](https://github.com/bloodborne-native/bloodborne-recomp/blob/main/docs/RECOMPILATION.md): a detailed AOT-function translation and behavioral-check strategy. Their published 2026-11-02 report cites 96.2% instructions recompiled, 86% CPU time running in recompiled code, **but the published architecture still uses a translator fallback** and user-owned PS4 executable as offline input. We must not count those translated-fallback paths as a completed native game or copy generated proprietary code into public GitHub. Investigate import/call closure, native OS threading, library replacement and actual gameplay replays without interpreter fallback.
- [droogie/bbhost #73](https://github.com/droogie/bbhost/pull/73), **open**: FSR, DLSS, Reflex and frame generation ideas; capability checks, licensing and benchmarks required before any vendor feature is integrated into the strict native port.
- [KhronosGroup/Vulkan-Docs](https://github.com/KhronosGroup/Vulkan-Docs), [GPUOpen VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator), [ValveSoftware/Proton](https://github.com/ValveSoftware/Proton), [doitsujin/dxvk](https://github.com/doitsujin/dxvk), [HansKristian-Work/vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton): relevant Vulkan synchronization/memory and optional compatibility comparisons, not imported into the current code.

Use repeatable targeted scans by subsystem across branches, PRs, forks and linked repos; no responsible engineering process can truthfully claim a complete census of "all GitHub".

## Next critical path

1. **V373 Windows D3D12 indexed draw parity**: same packed layouts and verification contracts on a real Windows WARP render target, byte-for-byte/pixel-level checks, to match V370/V372 Vulkan.
2. **True Bloodborne 3D render**: safely construct actual private FLVER mesh draw lists, topology-aware index buffers and transforms; material/texture/animation/skeleton support with correct native shaders. Keep private validation entirely private.
3. Native Linux/Windows SDL3 window/swapchain, render loop, async frame fences and shader pipeline cache; p50/p95/p99 frame pacing and VRAM residency measurements on physical GPUs before claimed optimizations.
4. **Parallel and more fundamental**: whole-game v1.09 static AOT/native import closure, no PS4 ELF or interpreter at runtime. A triangle rendered does NOT equal playable Bloodborne.
5. Later, once correct offline gameplay is established, honor all user-requested performance, K+M chord remapping, dedicated jump, controllers/HUD glyphs, manual NG+, QoL/mods, online co-op/invasions/LAN/dedicated/server selection, modern DLSS/FSR/XeSS/Reflex/HDR/VRR and shader warmup features as tracked in V366's complete backlog.

**Non-destructive:** Stacked Draft PR from V371. No automatic merges, production Fornex service writes, player-save changes, or private original game uploads.

## Verified post-review regression

The final V372 CI additionally recompiles and executes the **unchanged public V370 stride12 drawing test** under both GCC and Clang (besides the new packed 44/36-byte path), preventing regressions in existing callers. Actual lavapipe pixel readbacks remained 1,094 visible/0 offscreen for V370 as well as V372. Clang ASan/UBSan also passed the V372 packed layout path. No validation errors were observed in the relevant log messages. The V372 branch remains stacked Draft and does not contain or execute copyrighted game data.
