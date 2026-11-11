# Native V362: FLVER2 geometry contract and broad GitHub donor scan

Date: 2026-11-11. Parent: `feature/native-v361-safe-bnd4-index-20261111`.
Goal: independent **no-runtime-EBOOT/no-runtime-PS4-ELF** Windows Bloodborne, not BBPort's existing guest-ELF execution path.

## Implemented source

- `native_flver2_geometry_v362.{h,c}`: standalone data-only C parser for narrow FLVER2 0x20013/0x20014 little-endian variants; explicitly refuses unknown versions and endianness.
- Validates file size, data offset/length, 0x80-byte FLVER header and record-array bounds for dummies, materials, bones, meshes, face sets, vertex buffers, buffer layouts and textures.
- Validates vertex layouts and per-member packing widths, vertex stride and byte count, face-set index count/width/byte count, geometry data ranges, mesh material/bone references, mesh-to-face/vertex-buffer lists, all referenced index values (including the reserved restart sentinel).
- O(1) auxiliary memory; **not** a full vertex layout decoder, skeleton/animation engine, FLVER exporter, or native GPU render path. It does not allocate, execute game scripts or read anything from the filesystem.
- Source-only `test_native_flver2_geometry_v362.c`: invented geometry, header failure, endian/version refusal, overflow/truncation, malformed face/vertex buffer/layout, illegal mesh references, invalid triangle indices, and empty geometry cases.
- CI `native-v362-flver2-geometry.yml`: native Windows x64 clang-cl and Linux Clang/GCC; Linux sanitizer coverage for invented fixtures. No private inputs enter public CI.

## Private owner-data validation (metadata only)

Actual decrypted game resources are located in owner-private Drive; they were unpacked in a private workspace and inspected by a C parser compiled **from the same FLVER2 source**. No private bytes, filenames of hidden locations, proprietary generated model data or executable output are committed.

| Private file origin | Decoded FLVER2 bytes | Version | Meshes | Vertex buffers | Face sets | Vertices | Index elements | C probe |
|---|---:|---|---:|---:|---:|---:|---:|---|
| Bloodborne CUSA03173, `c9010.chrbnd.dcx` | 608 | 0x20014 | 0 | 0 | 0 | 0 | 0 | accepted |
| Dark Souls III PC, `c6281.chrbnd.dcx` | 5,952 | 0x20014 | 0 | 0 | 0 | 0 | 0 | accepted |
| Bloodborne CUSA03173, `c9942.chrbnd.dcx` | 487,584 | 0x20014 | 1 | 1 | 6 | 5,825 | 105,120 | accepted |
| Dark Souls III PC, `c6231.chrbnd.dcx` | 940,512 | 0x20014 | 4 | 4 | 24 | 11,875 | 192,132 | accepted |

**Evidence limits:** Four samples represent only a small subset of all original assets. Passing a metadata contract does not prove complete mesh rendering, skinning, correct GPU uploads, or all geometry variants in Bloodborne.

## Broad GitHub search: independently useful source categories

This pass searched repository names/description and known upstream layouts for FLVER, Bloodborne native/recomp, formats, mesh import, rendering, original host/runtime and fork families. GitHub's search is ranked/paginated and continually changes: **this is a deliberate broad pass, not a claim that every repository, PR, branch or private repo on GitHub was exhaustively read.** Additional queries/forks should be checked when the next subsystem requires them.

| Repository | Useful for strict native port | Important qualification |
|---|---|---|
| [JKAnderson/SoulsFormats](https://github.com/JKAnderson/SoulsFormats) | Reference FLVER2 fixed-size structures, faces, vertex layouts and binder semantics | .NET, GPL-3.0; implementation not directly imported into C |
| [soulsmods/SoulsFormatsNEXT](https://github.com/soulsmods/SoulsFormatsNEXT) | Actively maintained multi-game format variants, Bloodborne/DS3 DCX/BND/FLVER | GPL-3.0; test/format reference, not a native Windows engine |
| [Kalmarv/fromsoft-formats](https://github.com/Kalmarv/fromsoft-formats) | Rust parser, bounds discipline, archive formats, model vertex data and other From formats | Its documented primary scope is Sekiro/Elden Ring; BB-specific compatibility not assumed; GPL-3.0 |
| [Meowmaritus/SoulsAssetPipeline](https://github.com/Meowmaritus/SoulsAssetPipeline) | End-to-end model import/export pipeline and representation conversion clues | Depends on SoulsFormatsNEXT; GPL-3.0, not a rendering engine |
| [ividyon/WitchyBND](https://github.com/ividyon/WitchyBND) | DCX/BND roundtrips and variant/error fixtures | Uses bundled dependency ecosystem, including external compression; inspect licensing per component |
| [vawser/Smithbox](https://github.com/vawser/Smithbox) | Material/vertex model and mod editing behavior | Editor-specific assets; no direct runtime transplant |
| [asasasasasbc/FLVER_Editor](https://github.com/asasasasasbc/FLVER_Editor) | Additional FLVER structures and edited-asset edge cases | Test-only donor candidate; independently verify formats and license |
| [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp) | Original function graph/AOT recompiler and code coverage, target CUSA03173 1.09 | Native library generation retains interpreter fallback; does not prove fully independent Windows gameplay |
| [Yharnam-Hunters/Paleblood](https://github.com/Yharnam-Hunters/Paleblood) | Function-by-function verified rewrite and new graphics/runtime reconstruction, including partial native renderer | Explicitly not a complete playable game; its current intermediary runtime is not automatically strict no-runtime-ELF |
| [Astrr00/BloodbornePC](https://github.com/Astrr00/BloodbornePC) | Independent Windows C++ static recompilation, gameplay, graphics, audio and save implementations | Author describes ~60% estimate; no complete no-EBOOT full-game proof; verify 1.09 vs older binary assumptions |
| [droogie/bbhost](https://github.com/droogie/bbhost) | Extensive import coverage, engine-level GPU semantics, Vulkan renderer modernization and live gameplay behavior | Loads original PS4 ELF; donor for ideas/ported functions only, not finished strict Windows-native runtime |
| [deadinside28/bloodborne_pc](https://github.com/deadinside28/bloodborne_pc), [Mrsuss60/bloodborne_pc_windows_port](https://github.com/Mrsuss60/bloodborne_pc_windows_port), [visy/bloodborne_pc_windows_port](https://github.com/visy/bloodborne_pc_windows_port) | Compatibility baseline, GPU fixes, audio/input, Windows integration and shaders | Existing playable paths load PS4 code; never relabel them as native source ports |
| [shadps4-emu/shadPS4](https://github.com/shadps4-emu/shadPS4) | PS4 GPU/resource behavior and regression reference | Emulator; never a runtime dependency for the final port |

Use licenses/provenance/third-party obligations **per file** before copying code. The new C parser is independently authored based on format observations and public structural descriptions; no third-party source files were pasted into it.

## Additional PR and branch review (not limited to default branches)

Global GitHub PR search identified useful changes that would have been missed
by looking at only a repository's README:

- [SoulsFormatsNEXT PR #56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56)
  (merged, 2026-08-13): FLVER2 can be inspected **without fully
  materializing vertices**; consumers can manage GPU buffer IO themselves.
  V362 follows the same principle but is an independent C validator.
  Future data ownership and GPU uploads should maintain this separation.
- [SoulsFormatsNEXT PR #58](https://github.com/soulsmods/SoulsFormatsNEXT/pull/58)
  (merged, 2026-10-24): temporary allocations removed from its reader,
  pooled buffers and span-based paths. Investigate a bounded slice/cache
  approach for our native asset streamer instead of per-file copies;
  do not import .NET runtime structures.
- [SoulsFormatsNEXT PR #55](https://github.com/soulsmods/SoulsFormatsNEXT/pull/55)
  (merged, 2026-07-01): multiple vertex positions/normals for cloth.
  Ensure future FLVER vertex decoder supports repeated semantics; V362
  **does not decode** these values and should never claim compatibility.
- [SoulsFormatsNEXT PR #39](https://github.com/soulsmods/SoulsFormatsNEXT/pull/39)
  (merged, 2025-08-04): material tiling U/V properties were previously
  misnamed; keep PC material settings tied to observed semantics.
- [Paleblood PR #496](https://github.com/Yharnam-Hunters/Paleblood/pull/496)
  (closed without merge as of this review): compressed BC1/BC4 Vulkan
  images must not be initialized using invalid `vkCmdClearColorImage`
  operations. Validate upload transitions with `VK_LAYER_KHRONOS_validation`.
  Treat as a candidate regression, not proof the fix was merged.
- [Paleblood PR #560](https://github.com/Yharnam-Hunters/Paleblood/pull/560)
  (open draft, 2026-11-11): engine-specific opaque auto-draw packet
  reconstruction; gameplay reachability and GPU execution are explicitly
  unverified. Do not transplant as a known renderer fix.

These are tracked **research inputs**, not silently merged code.
Any reuse requires independent reproduction, license compatibility and
real Bloodborne 1.09 test evidence.

## Priorities after V362

1. Validate the complete V360→V361→V362 flow on synthetic end-to-end resources and a larger private sample set, with guards against malformed BND entry ranges; build native mesh upload descriptors with explicit lifetime ownership.
2. Material/texture/FLVER parsing, transform/skeleton and format variant negotiation, then *real* Vulkan/DirectX resource upload and render smoke, not synthetic-only geometry.
3. Continue full original 1.09 function AOT + Win64 native call graph/import closure, no runtime guest interpreter/fallback, then whole-game offline launch without ELF.
4. Only after proven offline gameplay: stable online, matchmaking/co-op/invasions, performance/QoL and renderer settings.

No changes to Fornex, real game files, saves, playable BBPort or Yharnam Together. The original game assets stay private.
