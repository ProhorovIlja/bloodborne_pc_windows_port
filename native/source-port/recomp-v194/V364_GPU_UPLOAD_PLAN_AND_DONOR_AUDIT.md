# Native V364 — renderer-neutral FLVER2 GPU upload planning

Date: 2026-11-11. Base: `feature/native-v363-dcx-bnd4-flver-pipeline-20261111`.
Branch: `feature/native-v364-renderer-neutral-gpu-staging-20261111`.

## Objective and precise scope

Continue a **strict no-runtime-EBOOT/PS4-ELF** Windows Bloodborne port by preparing validated CPU-side geometry upload plans. This is a source-only data-engine component, **not** a Windows game executable, Vulkan or Direct3D renderer, actual GPU upload, shader translator, performance benchmark, gameplay or multiplayer.

## Implemented

`native_flver2_gpu_plan_v364.{c,h}` exposes read-only FLVER2 upload metadata without memory allocation or source-data copying:

- Revalidate V363's immutable source model through V362 rather than trusting a potentially stale summary. The model must remain alive and unchanged during planning and until staging is complete.
- Discover exact output array sizes through `shyt_native_flver2_gpu_requirements_v364`: vertex spans, index spans, per-mesh/face draw records and packed staging bytes.
- `shyt_native_flver2_gpu_plan_v364` emits explicit, relative byte offsets and sizes for all vertex/index streams, vertex strides, layout IDs, index widths (16/32), primitive topology, culling, material and mesh relationships; preserves face flags for later LOD/motion-blur decisions. It does not create GPU buffers.
- Each span receives a **4-byte-aligned staging offset**. A caller-specified staging-byte budget is enforced before any descriptor is written. Empty models produce an empty plan. Never emit GPU copies of zero-length slices.
- `shyt_native_flver2_stage_bytes_v364` copies an explicitly bounded model span into caller/backend-owned staging RAM only after checking full offset, destination size and disjointness from **the whole original model memory**. Failure writes no bytes and sets `*written=0`. Caller is responsible for keeping the source model alive and immutable and for preserving staging memory until the GPU transfer has finished.
- Renderer-specific implementation must honor appropriate GPU buffer usage bits, upload barriers, allocation limits, element alignment, texture/vertex decoding, pipeline topology and synchronization. A 4-byte staging alignment is a convenient conservative layout, **not** a proof of Vulkan/Direct3D validity.
- No dynamic memory allocation, filesystem reads, game-origin bytes, external executable code, PS4 guest CPU, GPU commands or private assets in this source module.

## Tests

- `test_native_flver2_gpu_plan_v364.c` builds deterministic invented one-mesh/one-vertex-buffer/one-face-set and zero-geometry FLVER2 fixtures. It checks metadata, byte-for-byte staging copies, budget rejection, insufficient array capacities, offset out of range, aliasing rejection, corrupted triangle indices, malformed file sizes, zeroed failure outputs and immutable-buffer contract. The test uses zero original game data.
- `.github/workflows/native-v364-gpu-staging.yml`: Windows clang-cl and Linux GCC/Clang plus ASan/UBSan; no private game inputs or zlib dependency because V364 starts from the validated V363 model view.
- Private local-only probes **using the exact same V364 parser implementation** accepted four previously extracted, owner-supplied Bloodborne/DS3 FLVER2 samples. Two are geometry-empty; the others have:
  - Bloodborne: 1 vertex stream, 6 index streams and 6 planned draws; 256,300 vertex bytes, 210,240 index bytes, **466,548 packed staging bytes** (8 padding bytes).
  - Dark Souls III: 4 vertex streams, 24 index streams and 24 planned draws; 522,500 vertex bytes, 384,264 index bytes, **906,784 packed staging bytes** (20 padding bytes).
  - Both observed non-empty samples used triangle-list face sets and contained no primitive restart sentinel. This is *only* for those two private fixtures; do not assume all assets use triangle lists.
  - Never commit extracted models, binaries, texture names, runtime addresses or other proprietary contents. Original data stays in the owner's private folder.

## Cross-repository and graphics API research

- [SoulsFormatsNEXT PR #56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56) provides an established model of parsing FLVER metadata without materializing individual `Vertex` objects. The V364 code uses the same broad objective with independently written bounded C logic, **not copied upstream code**.
- [SoulsFormatsNEXT PR #58](https://github.com/soulsmods/SoulsFormatsNEXT/pull/58) shows that avoiding transient parse allocations matters; V364 plan descriptors are caller-provided and do not allocate per-vertex objects. No speedup claims without measurements.
- [Paleblood PR #463](https://github.com/Yharnam-Hunters/Paleblood/pull/463) explores batching Vulkan draw/dispatch submissions; it is a **future renderer integration** item, not incorporated here.
- [Khronos Vulkan spec: buffer copies](https://docs.vulkan.org/spec/latest/chapters/copies.html) specifies copy-source/destination usage, in-bounds regions and avoiding source/destination alias hazards. Use Vulkan validation layers before claiming real uploads.
- [Khronos Vulkan spec: indexed drawing](https://docs.vulkan.org/spec/latest/chapters/drawing.html) distinguishes uint16/uint32 indices and list/strip topology; primitive restart needs careful handling and must not be inferred from format name alone.
- The no-runtime-ELF game's primary AOT/source reconstruction remains larger and independent of this resource pipeline. The playable BBHost/BBPort PS4-loader path must **not** be relabelled fully native.

Search is targeted and paginated: not an assertion that all GitHub repositories, forks, PRs and branches were exhaustively inspected. Candidate code imports require compatibility and license/provenance review per component.


### Additional source-port architectures checked in the public GitHub search

- [Astrr00/BloodbornePC](https://github.com/Astrr00/BloodbornePC) describes a Windows x86-64 recompiler that emits C++ and a local compiled `bbgame.exe`, with differential testing of generated guest functions. Its [ARCHITECTURE](https://github.com/Astrr00/BloodbornePC/blob/main/docs/ARCHITECTURE.md) and [ROADMAP](https://github.com/Astrr00/BloodbornePC/blob/main/docs/ROADMAP.md) are important donors for function-boundary discovery, test harness design and cross-ABI semantics. Its documented `bbgame <eboot.bin>` path maps ELF data at runtime, so **its published flow cannot be called our strict no-runtime-ELF target as-is**. Performance/playthrough percentages in its README are maintainer claims, not our independent verification.
- [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp) includes meaningful AOT speed optimizations and instruction-family coverage; its current fallback to `bbcpu` for unsupported instructions likewise does not satisfy our final no-interpreter runtime constraint.
- [Yharnam-Hunters/Paleblood](https://github.com/Yharnam-Hunters/Paleblood) supplies a careful function-by-function oracle and native runtime model, with an explicitly incomplete original-game rewrite. Its status is not equivalent to a fully native game release.
- [Awakenchan/LanternEngine](https://github.com/Awakenchan/LanternEngine), [Jgamrot/yharnam-pc](https://github.com/Jgamrot/yharnam-pc), [RandomAlien0x33/bloodborne-win-native](https://github.com/RandomAlien0x33/bloodborne-win-native), and [theitsnschool/bloodborne-windows-native-loader](https://github.com/theitsnschool/bloodborne-windows-native-loader) all describe working PC-host paths that **still load the original PS4 game code**. They are useful reference implementations for stability, input, shader caching, memory modes, network and UX, not replacements for an ELF-independent Windows executable.
- The upstream corpus should be revisited by **subsystem, issues, branches and PR diffs**, with actual test cases and license checks. A ranking search and eight README inspections are not an exhaustive scan of every GitHub fork or private repository.

## Important remaining work

1. Add a real Vulkan/Direct3D allocation and staging backend (separate PR), with validation layers, buffer-usage flags, copy-region safety, synchronization fences, and GPU memory residency/eviction budgets; verify frame-time and memory changes on representative original scenes.
2. Decode actual FLVER vertex semantic/layout variants, bone transforms, geometry instancing and material textures, including compressed formats and LOD; preserve model->stage->GPU lifetime explicitly.
3. Continue native original-game 1.09 AOT/import and callback closure, new Win64 renderer/physics/input/audio/save and offline gameplay with NO runtime guest PS4 executable or interpreter; only then multiplayer and performance/QoL integration.
4. Re-run a privacy-preserving original-game fixture corpus and fuzz damaged data; source-only synthetic CI cannot prove all Bloodborne model variants are supported.

No Fornex, gameplay saves, production Yharnam Together, original game files, or executable dumps were changed by V364.
