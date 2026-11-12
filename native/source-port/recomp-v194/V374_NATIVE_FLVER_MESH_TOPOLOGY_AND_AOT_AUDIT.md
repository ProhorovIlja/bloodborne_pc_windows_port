# Native V374 — verified owner-private FLVER2 mesh / face / LOD topology

Date: 2026-11-12. Head branch: `feature/native-v374-private-mesh-topology-20261112`, based on V373 Windows D3D12 WARP draw.

## Strict port target

Independent Bloodborne for Windows and Linux, running no original PS4 EBOOT/SELF/ELF, Orbis guest ABI/HLE, emulated PS4 CPU or GPU command stream during execution. User-owned original game executable can be researched or statically converted **offline**, but must not be shipped, embedded or uploaded publicly. A port that loads PS4 ELF at runtime, even if it uses native D3D12/Vulkan for graphics, does not meet this requirement.

## V374 source implementation

The portable C11 module `native_flver2_mesh_topology_v374.{h,c}` builds on the V362 completely validated FLVER2 0x20013/0x20014 file parser and independently walks mesh headers, face-set refs, vertex buffer indices and element arrays.

- `shyt_native_flver2_mesh_face_v374`: inspect one named mesh and face slot with validated material, default-bone index, local bone-count metadata, up to 3 vertex-buffer indices, actual vertex count and 16/32-bit index stream bounds, LOD0/1/2, motion-blur flag, cull flag and topology. Unknown flags, ambiguous LOD categories and EDGE-compressed indices are rejected, never silently interpreted as ordinary triangles.
- `shyt_native_flver2_triangles_v374`: count or emit source-owned triangle-list vertex indices. For a triangle list, require 3N index elements. For strips, handle 16-bit 0xFFFF or 32-bit 0xFFFFFFFF primitive restart, reset winding on restart, preserve parity across degenerate triangles, and drop degenerate triangles. Refuses ambiguous 16-bit restart when the vertex space reaches the restart sentinel; every non-restart index must be inside the mesh's vertex range. Output uses explicit caller-owned uint32 indices and strict capacity. Two-pass scan first validates source and capacity, then emits: no partial writes on failed preflight.
- Allocation-free, no renderer/GPU work, no original game data, no file/OS/network access or mutable globals; rejects all data-output aliasing and malformed ranges. Suitable for a future immutable asset loader, **not** for repeatedly rescanning the file each frame.

Public invented fixtures: 
- 16-bit triangle list: 2 triangles, no degenerate or restarts.
- 16-bit triangle strip with a restart: 3 triangles, correct alternating winding.
- 32-bit motion face list: 1 nondegenerate triangle and 1 degenerate dropped.
- 32-bit strip: validates winding through two degenerates and 32-bit restart.
- LOD1, LOD2 and motion categories; fail-closed for unsupported LODEx/unknown flags, combined LOD1+LOD2, out-of-range indices, sentinels inside triangle lists, truncated data, too-small output buffers, and source/metadata output aliases.

CI — **both Windows and Linux passed**: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/43177734491
- Ubuntu24 GCC/Clang with strict C11 warnings + Clang ASan/UBSan.
- Windows2022 clang-cl C11, strict /W4 /WX.
- Public CI uses only the synthetic fixtures above; private original game files are never sent to runners.

## Owner-private Bloodborne / Dark Souls III actual input validation

The exact C11 V374 source code was compiled privately with Clang ASan/UBSan and run over **two intact real FLVER2 payloads extracted from the owner's private game assets**; this test must not be mistaken for public GitHub CI:

| Observed property | Bloodborne CUSA03173 sample | Dark Souls III PC sample |
|---|---:|---:|
| FLVER bytes, kept private | 487,584 | 940,512 |
| Actual meshes | 1 | 4 |
| Active vertex buffers / vertices (V371) | 1 / 5,825 | 4 / 11,875 |
| Face sets, all validated and enumerated | 6 | 24 |
| Visible, non-motion LOD0 triangles | 9,187 | 17,574 |
| Visible, non-motion LOD1 triangles | 5,511 | 10,542 |
| Visible, non-motion LOD2 triangles | 1,836 | 3,513 |
| Motion-blur LOD0 triangles after removing degenerate faces | 9,933 | 17,924 |
| Motion-blur LOD0 degenerate faces skipped | 258 | 24 |

Bloodborne face slots carry the same conceptual categories as the sampled DS3 data: three ordinary LOD sets and three corresponding motion-blur sets. The material index/default bone and face/vertex refs were validated; no original bone hierarchy, keyframes or skin matrices have been reconstructed. Rendering ALL face sets simultaneously would overdraw geometry and waste bandwidth; the application must choose the appropriate LOD and motion-blur variant per pass. These counts describe just **two character-resource examples**, not the entire game or all meshes/LOD conventions.

All public source and CI tests use invented arrays and fabricated indices. Proprietary original sample files were never added to GitHub, CI or a user-facing downloadable package; private model bytes stay in the owner's private research area. The private harness itself lives outside the public repo. No private `.flver` or `.dcx` file belongs in the public source handoff folder.

## Sources and broad GitHub audit

- [JKAnderson/SoulsFormats — FLVER2 FaceSet](https://github.com/JKAnderson/SoulsFormats/blob/master/SoulsFormats/Formats/FLVER/FLVER2/FaceSet.cs) and [SoulsFormatsNEXT FaceSet](https://github.com/soulsmods/SoulsFormatsNEXT/blob/master/SoulsFormats/Formats/FLVER/FLVER2/FaceSet.cs) document the distinction among triangle lists/strips, primitive restarts, degenerates and face-set LOD/motion flags. Source code here was independently written, not copied from the GPL-licensed donor implementation.
- [SoulsFormatsNEXT #55](https://github.com/soulsmods/SoulsFormatsNEXT/pull/55) enables multiple vertex-position/normal semantic layers, important for cloth/meshes beyond our V371 restricted layouts.
- [SoulsFormatsNEXT #56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56) permits reading FLVER without eagerly materializing every vertex; #58 reduces binary reader overhead. Both support the future streaming design, subject to licensing and owner-data tests.
- [Paleblood #655](https://github.com/Yharnam-Hunters/Paleblood/pull/655) adds hardware tessellation/geometry shader-stage detection; [Paleblood #652](https://github.com/Yharnam-Hunters/Paleblood/pull/652) covers indirect draw semantics. Both were verified as merged on 2026-11-12 and are format/behavior references for a more complete renderer, not code integrated in V374.
- [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp) has substantially advanced portable static recompiler research. Its current README reports 10,284,725/10,691,122 instructions handled (~96%), and 181,521/181,570 functions recompiled, with opt-in runtime and translator fallback. Its GPU and OS emulation/runtime dependency work is separately in `bloodborne-runtime`. This is a much more relevant donor for the **whole-game AOT/import-closure critical path** than adding ever more isolated asset decoders; no claims of a completed native Windows/Linux client are justified by these counters alone. Check [recompilation detail](https://github.com/bloodborne-native/bloodborne-recomp/blob/main/docs/RECOMPILATION.md), generated library dependencies and license/provenance before adaptation.
- [GPUOpen D3D12MemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator), [VulkanMemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator), [Valve Proton](https://github.com/ValveSoftware/Proton), [DXVK](https://github.com/doitsujin/dxvk) and [VKD3D-Proton](https://github.com/HansKristian-Work/vkd3d-proton) remain candidates for optimized memory management and compatibility cross-tests, not mandatory runtime dependencies of independent native builds.

This is a targeted, extensible GitHub donor review; it is not a claim to have literally enumerated all public and private repositories, PRs, branches and issues. Per-file licensing and provenance checks precede any import.

## Remaining critical work

1. **Native true-game geometry**: map user-private Bloodborne mesh bones, bind pose, bone influence types, matrix transforms, material/shader/texture associations, and LOD draw selection into a correct scene; test only locally against the owner's private assets. V374 counts/triangulates real game indices but does not rasterize the complete original model.
2. **Vulkan + D3D12 render generalization**: batch arbitrary mesh index ranges rather than only the synthetic 3-index triangles from V370/V373; bind per-object transforms, depth and correct topology, add async render/present and GPU resource pools with measured p95/p99 frame times and shader warmup. Implement device-loss rollback before deployment.
3. **Source-native AOT main blocker**: use the portable recompiler's function-level evidence and replay methodology to identify *all* unhandled BB1.09 imports, self-patching code, lib/OS services and guest-runtime dependencies. The target is a compiled native Win64/Linux game with **zero runtime guest-code fallback and zero original PS4 executable loading**, not a compatibility-layer wrapper.
4. After complete offline game + Old Hunters + chalices validates, implement the long-term user backlog tracked in V366: independent native controls, full key/chord remap, separate jump button, controller icons, manual NG+, shader-cache/prewarm, upscalers, latency technologies, HDR/VRR, save safety, QoL, mods, LAN/online/invasions, server selection and dedicated hosting. Measure, do not promise zero network latency or universal FPS.

Safety: preserve original game files/saves and all production Fornex/Ultimate Yharnam Together systems. Leave Draft PR stacks unmerged until correctness and provenance review. The V374 portable source C parser has no runtime device emulator or original game binary dependency.
