# Native V371 — verified real Bloodborne and Dark Souls III FLVER2 vertex semantics

Date: 2026-11-12. Base: `feature/native-v370-vulkan-offscreen-flver-draw-20261112` (Draft PR #100). Feature: `feature/native-v371-flver-real-vertex-semantics-20261112`.

## Purpose and genuine progress

V370 successfully rasterized an **invented** float3 triangle through native Linux Vulkan. V371 begins adapting that renderer to actual owner-provided Bloodborne and Dark Souls III character assets by independently validating and decoding their real FLVER2 vertex layout. The final goal remains an independently executable native Windows/Linux game without runtime PS4 EBOOT/SELF/ELF, guest-code interpreter, PS4 ABI/HLE, shader translation of guest commands, Proton or Wine. Native data decode alone does NOT satisfy that goal.

**Public code**: `native_flver2_vertex_decode_v371.{h,c}` (strict C11, allocation-free), and `test_native_flver2_vertex_decode_v371.c` (invented bytes only). Reuses V362 metadata/geometry validator. It does not copy third-party implementation code and publishes no original game bytes, asset-derived models, filenames of hidden personal resources, secrets or saves.

The source accepts only verified little-endian FLVER2 v0x20013/v0x20014 and currently checks *all* global vertex buffers independently. A validated layout exposes bounded semantic/type/index/offset/stride data. A second function decodes a bounded vertex slice into caller-provided canonical C structs containing position, normal, two tangents, two UV pairs, optional bone indices/weights, color and a presence bitmask. Its output is not a skinning transformation or a GPU upload; the source remains immutable, and all output must be disjoint from the entire input file. Unsupported semantic/type combinations are rejected, not fabricated. Nonfinite positions, overflowing ranges, repeated position/normal/tangent slots and missing bone index/weight pairing are rejected. The decode preflights the requested slice before writing, preventing partial writes on late nonfinite values.

## Real private parity: source of truth, not public test data

Original resources were read **only from the owner's private `gungrain@gmail.com` Google Drive** and decompressed in a local private workspace. Their bytes were never included in code, Actions, commits, handoff attachments, public output or build artifacts. The small C probe used the same checked-in V362 and V371 C source with Clang ASan/UBSan. This is **private actual-asset verification**, separate from public reproducible CI.

| Owner-private asset | Internal FLVER bytes | Global vertex buffers | Meshes | Decoded vertices | Layout(s) observed | Local Clang ASan/UBSan |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Bloodborne CUSA03173, character binder | 487,584 | 1 | 1 | **5,825** | 44-byte active, 36-byte additional descriptor | PASS, all 5,825 |
| Dark Souls III PC, character binder | 940,512 | 4 | 4 | **11,875** | 44-byte active, 36-byte additional descriptor | PASS, all four buffers |

All **five** active vertex buffers use a common 44-byte layout with eight members: `Float3` position at offset 0; `Byte4B` normal at 12; two `Byte4B` tangents at 16/20; `Byte4B` bone indices at 24; `Byte4C` weights at 28; `Byte4C` vertex color at 32 (semantic index 1); `UVPair` at 36 (two signed-short UV coordinate pairs). Each selected sample contains a second 36-byte *layout descriptor* with fewer members; no claim is made that the sampled meshes' active buffers use that descriptor. The 36-byte case is independently covered by fabricated synthetic tests.

Decoding uses narrowly verified format rules: LE IEEE754 float3, packed normal/tangent components `(unsigned_byte - 127) / 127`, four unsigned byte indices, unsigned byte weights/colors divided by 255, and two pairs of signed 16-bit UV components divided by 2048 for these FLVER versions. The 4th normal byte is preserved as raw `normal_w` metadata. **No weight renormalization, bone palette lookup, skeleton animation, position normalization, coordinate-space conversion or texture sampling is performed.** These require later independently validated engine stages. Unknown EDGE compression, unsupported layout types, repeated position/normal semantics or novel layouts are refused by design.

## Public CI

Workflow: `.github/workflows/native-v371-flver-vertex-semantics.yml`.

- Ubuntu 24.04: GCC and Clang strict C11 with `-Wall -Wextra -Werror -Wconversion`, plus real Clang AddressSanitizer/UndefinedBehaviorSanitizer execution.
- Windows Server 2022: `clang-cl /TC /std:c11 /W4 /WX` compile and actual invented fixture execution.
- Synthetic full 44-byte skinned layout and 36-byte unskinned layout; standalone float3-only V370 input contract; exact decoded positions/normals, tangents, indices, weights, color and signed UVs.
- Negative cases: truncated FLVER, incompatible format/semantic/semantic index, duplicate normals or tangents, invalid member offsets/stride, invalid source/output overlap, capacity and vertex range refusal, NaN position (entire output left untouched), and missing/unsupported features.
- No game data, original EBOOT, owner keys/saves, external proprietary shaders or DLC content in CI.

**CI success**: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43172098656 (both Windows and Linux PASS). This validates portable code on invented data, while the real owner-asset checks above were separately executed privately.

## Broad GitHub donor comparison

This pass checked relevant repositories and both merged and unmerged PRs, rather than relying on one first-found parser. Search is repeatable, targeted and incomplete by nature; we do **not** claim to have indexed the entire global GitHub/internet/Drive contents.

- [JKAnderson/SoulsFormats FLVER LayoutMember](https://github.com/JKAnderson/SoulsFormats/blob/master/SoulsFormats/Formats/FLVER/LayoutMember.cs): publicly documented numeric LayoutType/LayoutSemantic meanings and normalization; .NET/GPL-3.0. The C implementation here is independently authored against original-asset observations; no GPL-3 implementation source copied.
- [SoulsFormatsNEXT #55](https://github.com/soulsmods/SoulsFormatsNEXT/pull/55) **merged** 2026-07-01: multiple positions/normals in cloth/ER. Our narrowly scoped V371 **rejects** duplicated position/normal semantics, so support for cloth/morph target variants is a clear future task, not an implied feature.
- [SoulsFormatsNEXT #56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56) **merged** 2026-08-13: read FLVER without materializing per-vertex managed objects. V371 likewise makes decoder output optional and caller-owned; the V364/V369 GPU upload path still supports binary ranges.
- [Paleblood #436](https://github.com/Yharnam-Hunters/Paleblood/pull/436) **merged** 2026-11-06: original GPU vertex fetch-shader and buffer-descriptor behavior. It provides independent compatibility research, but is based on PS4/GNM execution and is **not a runtime dependency** in our native port.
- [Paleblood #655](https://github.com/Yharnam-Hunters/Paleblood/pull/655) **merged** on 2026-11-12 (was open earlier that day): distinct geometry/tessellation shader stages must be handled or explicitly refused. Do not silently reinterpret special-stage draws as a plain vertex+pixel draw.
- [Paleblood #652](https://github.com/Yharnam-Hunters/Paleblood/pull/652) **open**: indirect draw semantics, GPU-generated argument requirements and barriers. Future render graph should have explicit path/capability gates.
- [droogie/bbhost #73](https://github.com/droogie/bbhost/pull/73) **open**, not merged: DLSS/FSR motion-vector reconstruction, frame generation and Reflex improvements. Relevant later, but not proof of ready or applicable native features.
- [GPUOpen VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator) and [GPUOpen D3D12MemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator): candidate pooling/residency libraries, not prerequisites for parsing true game vertex streams.
- [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp), [Astrr00/BloodbornePC](https://github.com/Astrr00/BloodbornePC), [Yharnam-Hunters/Paleblood](https://github.com/Yharnam-Hunters/Paleblood): continue parallel AOT/function-level reconstruction research because **graphics parsing is not the game itself**.

Per-file provenance and license compatibility must be evaluated before any code reuse. Upstream benchmark claims cannot be transplanted without independent profiling.

## Exact boundaries and next gates

- Supported: metadata and decoded attributes for two specific owner-confirmed model variants, with a reusable C API; synthetic tests under Windows and Linux; local private ASan/UBSan validation of 17,700 real vertices in total.
- Not yet: renderer interpretation of skinned vertex matrices, per-mesh bone palettes, animated skeletons, materials, textures, transparency, normal mapping, real character draw, original authored shaders, geometry/indirect draw, stable 60+ fps, or a native executable that boots the game.
- The 36-byte descriptor was seen on both original models but not used by the sampled active buffers. Its decoding is tested with generated **invented** data only.
- V372: bridge the decoded FLVER position semantics and index/topology to actual Vulkan and Direct3D12 draw tests, replacing the V370 hard-coded `float3` test assumptions; verify with privately owned real samples and no GPU uploads of copyrighted data in public Actions.
- Continue, in parallel, the **main blocking task**: full Bloodborne 1.09 game-function static AOT/import closure with no runtime guest interpreter, PS4 ELF or PS4 ABI dependency, then full offline playthrough correctness. After that, activate the long-term V366 remaster/controls/network/latency/upscaler/QoL feature roadmap.

**Safety:** no Fornex production write, game file mutation, save edit, private resource upload to public GitHub, or automatic merge of stacked Draft PRs.
