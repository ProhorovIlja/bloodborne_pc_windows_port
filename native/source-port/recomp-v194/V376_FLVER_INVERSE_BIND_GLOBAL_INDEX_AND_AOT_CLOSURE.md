# Native V376 — FLVER2 mesh bone palettes, inverse binds and explicit global-index skinning

Date: 2026-11-12. Base: `feature/native-v375-flver-bind-pose-20261112`.
Head branch: `feature/native-v376-mesh-skin-palette-20261112`.
This is **code and private-data research** for a future independent Bloodborne Windows/Linux executable; it is not a playable game or a complete animation system.

## Strict objective

A finished Windows/Linux native Bloodborne must run WITHOUT ever loading or interpreting the original PS4 EBOOT/SELF/ELF, without PS4 CPU interpreter/JIT, Orbis guest ABI/HLE or GNM/PM4 PS4 GPU command translation at runtime. User-owned game data may remain in the owner's local asset directory, and private 1.09 executable inspection/AOT generation may occur **offline** on the owner's machine. No proprietary game bytes, original shaders, private keys or save data are shipped with public CI.

## V376 implementation

The independently authored, allocation-free C11 module `native_flver2_skin_palette_v376.{h,c}` connects existing V362 whole-FLVER2 validation, V371 packed vertex decoding, V374 mesh layout and V375 bone bind-pose math, providing three separate safe capabilities:

1. `shyt_native_flver2_mesh_palette_v376` revalidates the original file and reads the mesh's indexed `int32` local-to-global bone table at mesh record offsets +20 and +28. Every palette member is bounded against the global skeleton, and the `dynamic` flag and default bone are returned without modifying the source. A zero-length palette is a valid **source fact**, not permission to invent its meaning. All capacity/overlap/malformed-list errors fail before any output element is written.
2. `shyt_native_flver2_inverse_binds_v376` creates **row-vector affine inverse bind matrices** from V375's original world bind transforms. It checks all 4x4 components for finite values, row-affine structure, near-singularity and inverse-product residuals before emitting any matrix. No external library or GPU API required. These are original inverse bind matrices, not animation transforms.
3. `shyt_native_flver2_skin_positions_v376` is a **CPU-only diagnostic**, applying each source vertex's four V371 bone weights and a caller-validated local-to-global palette using `(position * inverseBind[bone]) * animatedWorld[bone]` in a row-vector convention. It normalizes weights by their sum, rejects zero-total weights, out-of-range active bone indices, NaN/Inf, non-affine matrices and overlapping source/output pointers. It never guesses skeletal index semantics or imports animation.
4. `shyt_native_flver2_skin_global_positions_v376` is an **explicitly requested** variant for assets whose local palette was separately verified to be empty **and** for which the caller has independently accepted the hypothesis that active vertex byte indices are global skeleton indices. No automatic fallback from the local-palette API occurs. This produces the same result as an identity local-to-global map, but its name and docs intentionally expose the assumption.

Public invented test `test_native_flver2_skin_palette_v376.c`: synthetic FLVER2 mesh with a nonempty local palette; malformed palette, out-of-range index and aliasing; singular/non-affine/NaN inverse bind, no partial writes, non-uniform scale and 90-degree rotation; two-bone weighted skin at bind pose and on an invented animated pose, including 50/50 blend, late-invalid vertex, zero weights and explicit global-index mode. Linux GCC, Clang and ASan+UBSan passed locally before GitHub CI.

CI: `.github/workflows/native-v376-flver-skin-palette.yml`: Ubuntu 24.04 GCC + Clang and ASan/UBSan; Windows 2022 clang-cl C11 `/W4 /WX`, all on **synthetic-only** input. It does not test actual game files publicly.

## Private-only original asset verification, NO proprietary data published

The exact public C V376 module was built into a temporary local shared library and called over the owner's existing two decrypted, intact FLVER2 payloads in RAM. The game-owned bytes were not written into GitHub, Google public files, CI logs or user-visible downloads. The following aggregate results are not public CI results:

| Property | Owner's BB CUSA03173 sample (`c9942`) | Owner's DS3 PC sample (`c6231`) |
| --- | ---: | ---: |
| Bones / invertible global bind matrices | **123 / 123** | **142 / 142** |
| Meshes | 1 | 4 |
| Local mesh bone-palette entry count | **0** | **0 for all 4 meshes** |
| Mesh default bone index | 74 | 115, 114, 118, 119 |
| Vertices in 44-byte active buffers | **5,825** | **11,875** |
| Active nonzero-weight bone index maximum | 73 | 106 |
| Vertices with zero total weight | 0 | 0 |
| Vertices with weight-byte sum in [1,255] | 5,825 | 11,875 |
| Normal's `normal_w` in these samples | 0 for all | 0 for all |

- Private mathematical inversion check: highest absolute entry-wise residual of `inverse_bind * bind_world - identity` was about `1.61e-7` for BB and `1.23e-7` for DS3 (float32 stored matrices).
- **Explicit global-index assumption test:** feed all **17,700** original vertex positions, byte indices/weights and their current computed bind-world matrices through the V376 C global-index CPU diagnostic, then verify it reconstructs the input bind-pose positions. Each source model passes with largest absolute position error about **2.4e-7**. Every active raw byte index is within the skeleton's total bone count.
- **What this does NOT prove:** inverseBind×bindWorld is identity for any mathematically valid bone pairing, so this identity test alone CANNOT establish the correct in-game mapping of indices to bones, dynamic pose behavior, parent-skeleton HKX mapping, mesh placement/world origin, rotation/camera handedness, clothing/cloth bones, vertex normal skinning or cutscene animation. The global mapping is a **working hypothesis only**, gated behind the explicit API. With local palette count zero, doing a guessed automatic mapping would make wrong character deformations difficult to diagnose.
- The 44-byte vertex members, private skeleton graph and LOD mesh refs were separately checked in V371/V374/V375. No game bytes were compiled into public fixture or generated project.

## GitHub and internet source audit

Specific relevant sources checked (not a false claim to index literally all GitHub):

- [JKAnderson/SoulsFormats — FLVER2 Mesh](https://github.com/JKAnderson/SoulsFormats/blob/master/SoulsFormats/Formats/FLVER/FLVER2/Mesh.cs): `BoneIndices` is a mesh-owned list, distinct from `DefaultBoneIndex` and vertex-local byte indices. `Dynamic` influences pose interpretation; do not substitute default bone for weighted palette without independent evidence.
- [JKAnderson/SoulsFormats — FLVER Vertex](https://github.com/JKAnderson/SoulsFormats/blob/master/SoulsFormats/Formats/FLVER/Vertex.cs): `NormalW` is a separate rigid-bone convention for some layouts, not equivalent to weighted Byte4B indices. Our V376 weighted implementation does not silently consume `NormalW`.
- [JKAnderson/SoulsFormats — Bone](https://github.com/JKAnderson/SoulsFormats/blob/master/SoulsFormats/Formats/FLVER/Bone.cs): transform order Scale × RotX × RotZ × RotY × Translation; implemented and checked in V375.
- [soulsmods/SoulsFormatsNEXT #55](https://github.com/soulsmods/SoulsFormatsNEXT/pull/55) and [#56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56): multiple vertex normal/position semantics and direct GPU buffer-oriented reading, respectively. Both already merged. Unsupported variants remain explicitly rejected in the current strict subset.
- [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp), [recompilation report](https://github.com/bloodborne-native/bloodborne-recomp/blob/main/docs/RECOMPILATION.md): as of its 2026-11-02 report, 181,521/181,570 functions and ~96.2% instructions are compiled with residual translator calls, import stubs and patched code. Calls recorded/replayed against generated code cover only ~0.5% of recognized game functions. Its generated program still calls through `bloodborne-runtime` and PS4 executable memory; this is NOT strict standalone Windows/Linux.
- [bloodborne-native/bloodborne-runtime — executable](https://github.com/bloodborne-native/bloodborne-runtime/blob/main/docs/layers/executable.md): game still boots by loading/patching original PS4 executable; native entrypoint and native host memory layout **not done**.
- [bloodborne-native/bloodborne-runtime — system](https://github.com/bloodborne-native/bloodborne-runtime/blob/main/docs/layers/system.md): runtime still translates PS4 system requests (memory/thread/files/input/audio/video/network), even though it uses normal host implementations internally.
- [bloodborne-native/bloodborne-runtime — renderer](https://github.com/bloodborne-native/bloodborne-runtime/blob/main/docs/layers/renderer.md) and [GPU commands](https://github.com/bloodborne-native/bloodborne-runtime/blob/main/docs/layers/gpu-commands.md): GPU command state/engine render boundary research is more immediately helpful for a real native scene than extending isolated vertex parsing indefinitely; PS4 packet decoding still runs every frame on the donor and must ultimately disappear.
- [Paleblood #655](https://github.com/Yharnam-Hunters/Paleblood/pull/655): shader-stage discovery and fail-closed behavior for unsupported tessellation/geometry. [Paleblood #611](https://github.com/Yharnam-Hunters/Paleblood/pull/611): queue-submission batching. [bbhost #73](https://github.com/droogie/bbhost/pull/73) remains an unmerged upscaler/Reflex donor. Neither is a substitute for actual native game logic.

Before importing code or generated results, audit per-file GPL/other licenses and owner-game provenance. No source code from donor projects was copied into V376.

## Next critical path and realistic acceptance

**V377 should prioritize a verifiable whole-game AOT/native-entrypoint import-closure report and a machine-readable dependency inventory**, over yet another standalone geometry microfeature. Work from owner-only, build-time PS4 executable 1.09; identify functions/call edges still requiring interpreter, import handling, longjmp and runtime patch hooks. Generate an audit with counts and fail-closed CI gates, never ship owner code. A strict native milestone needs a Windows PE and Linux ELF executable that can start without loading any guest PS4 executable and without an interpreter or PS4 GPU packet translation. Only full offline game boot/progression/cutscenes/saves can prove the full port.

Alongside that path, future V378 renderer work should trace actual Bloodborne mesh bone relationships, HKX animation samples, validated weighted deformation (including normal/tangent skinning), GPU skin buffers and bind-pose transforms with synthetic tests and private-game verification. A real physical GPU/renderer/swapchain frame pacing test follows, then all user-requested controller and chord remapping, keyboard/mouse, dedicated jump, manual NG+, multiplayer/LAN/region/matchmaking, streaming, cache, DLSS/FSR/XeSS/Reflex and stability under the complete V366 backlog. Never promise zero internet latency.

**Safety:** do not auto-merge stacked Draft PRs; no writes or restarts on production Fornex, no player saves changed, no original files mutated, no private game bytes in public CI or GitHub, and do not break playable BBPort or BBSC: Yharnam Together Ultimate.
