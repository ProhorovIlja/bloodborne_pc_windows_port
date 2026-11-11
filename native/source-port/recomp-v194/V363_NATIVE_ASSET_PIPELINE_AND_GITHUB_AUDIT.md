# Native V363 — DCX → BND4 → FLVER2 asset pipeline and upstream audit

Date: 2026-11-11  
Parent: `feature/native-v362-flver2-geometry-contract-20261111`  
Feature branch: `feature/native-v363-dcx-bnd4-flver-pipeline-20261111`

## Objective and strict scope

The owner's primary objective is an independent native Windows Bloodborne
port, compiled to a Windows executable rather than launching an original PS4
`eboot.bin`/ELF or relying on a PS4 guest CPU, graphics HLE, and runtime.
V363 is a small, real **resource-data subsystem** for that objective. It is
**not** a game executable, game boot, renderer, physics engine, online mode,
network library, or proof of performance improvement.

## Implemented

- `native_dcx_bnd4_flver_v363.{h,c}` composes the source-only V360 DCX/Deflate
  reader, V361 BND4 index, and V362 FLVER2 geometry validator without adding
  any proprietary game code or memory allocation.
- `shyt_native_dcx_bnd4_open_v363`: streams one compressed DCX into caller-owned
  decoded scratch, validates a BND4 container, and exposes only a validated
  immutable view. The decoded archive is decompressed **once**, not once per
  selected file.
- `shyt_native_dcx_bnd4_flver_at_v363`: selects one binder index, refuses
  unsupported per-file compression, verifies file bounds and the inner FLVER2
  layout; publishes a zero-copy model view and geometry statistics.
- `shyt_native_dcx_bnd4_first_flver_v363`: scans the already validated binder
  for a supported FLVER2 magic after skipping non-model entries (TPF, HKX,
  other resources). It returns the actual file index. A FLVER candidate with
  an invalid or unsupported structure causes failure, rather than silently
  falling through to another file. All outputs are zeroed on failure, with
  `file_number = UINT32_MAX` on failed discovery.
- No filesystem access, no GPU calls, no dynamic allocation, no execution of
  game data; output points into scratch, which MUST remain alive and immutable
  while the view is used. Caller must never reuse scratch after failed open.
- `test_native_dcx_bnd4_flver_v363.c` creates invented DCX, BND4 and FLVER2
  resources. Tests both verified outer DCX header families, both verified BND4
  extended modes, valid mesh vertex/index metadata, corrupted checksums,
  malformed binder/FLVER, truncated reads, injected I/O failures, too-small
  output buffers, and per-file compression refusal. A three-entry synthetic
  binder models an actual Bloodborne TPF → FLVER → HKX ordering.
- `.github/workflows/native-v363-asset-pipeline.yml` tests pinned public zlib
  1.3.1 and the complete C chain on Windows x64 clang-cl, Linux GCC and Clang,
  plus AddressSanitizer/UndefinedBehaviorSanitizer for synthetic Linux fixtures.
  **No original game assets or game executables are in public CI.**

## Private original-game observations (metadata only)

Examined four owner-provided original-game resource archives *privately*.
The associated FLVER content was separately accepted by the V362 C validator
in the prior stage. The following DCX/BND/asset-order observations were made
with an independent bounded, local Python inspection; the **complete V363 C
adapter has not been claimed as tested on those private files**.

| Archive | BND entries | Model file index | Non-model siblings | DCX envelope / BND mode |
|---|---:|---:|---|---|
| Bloodborne `c9010.chrbnd.dcx` | 1 | 0 | none | 0x44/0x4C, `extended=0` |
| Bloodborne `c9942.chrbnd.dcx` | 3 | **1** | TPF first, HKX last | 0x44/0x4C, `extended=0` |
| DS3 PC `c6281.chrbnd.dcx` | 1 | 0 | none | 0x44/0x4C, `extended=4` |
| DS3 PC `c6231.chrbnd.dcx` | 3 | **0** | HKX and additional collision metadata | 0x44/0x4C, `extended=4` |

Other original Bloodborne GPARAM resources have the distinct
`DCX_DFLT 0x24/0x2C` envelope, which V360 already supports. This demonstrates
why hardcoded assumptions about "Bloodborne always uses 0x24" or "FLVER always
is file zero" are incorrect. These four archives are not representative of
all game assets. Per-entry compression, EDGE/KRAK and unverified BND variants
remain unsupported by this adapter and must fail safely.

## Cross-GitHub relevant changes, including PRs

This research pass followed current public repos, prior forks, and multiple
actual PRs. It is intentionally **not** a claim to have read every GitHub
repository/fork/branch/PR; indexed search and access permissions limit that.

- [SoulsFormatsNEXT PR #56](https://github.com/soulsmods/SoulsFormatsNEXT/pull/56)
  (merged): FLVER reading without materializing individual vertex objects;
  analogous to our zero-copy FLVER metadata contract. Reuse concept after
  format and license review, not .NET source code.
- [SoulsFormatsNEXT PR #58](https://github.com/soulsmods/SoulsFormatsNEXT/pull/58)
  (merged): reduced memory allocations in the reader using a buffered
  fast path. Future asset streaming should benchmark a bounded scratch
  allocator and avoid redundant resource copies.
- [bloodborne-native/bloodborne-recomp PR #7](https://github.com/bloodborne-native/bloodborne-recomp/pull/7)
  (merged): flat function table and per-thread batched counters; reports a
  10% drop in CPU time for its specific full AOT-library benchmark on M3 Pro.
  This is a candidate for OUR eventual native function-call dispatch, not a
  verified performance gain for a Windows Bloodborne.exe.
- [bloodborne-native/bloodborne-recomp PR #8](https://github.com/bloodborne-native/bloodborne-recomp/pull/8)
  (merged): explicit C generation for formerly interpreted instructions;
  valuable only if final execution stops depending on interpreter fallbacks.
- [bloodborne-native/bloodborne-recomp PR #10](https://github.com/bloodborne-native/bloodborne-recomp/pull/10)
  and [#11](https://github.com/bloodborne-native/bloodborne-recomp/pull/11)
  (merged): local vector-register state and reduced per-call TLS/filter
  checks. Review for an AOT call-path benchmark, with correctness tests.
- [Paleblood PR #463](https://github.com/Yharnam-Hunters/Paleblood/pull/463)
  (merged): batch Vulkan draws/dispatches in a command buffer instead of
  immediate queue waits; future independent renderer should evaluate this
  approach with synchronization/validation and frame-time benchmarks.
- [Paleblood PR #496](https://github.com/Yharnam-Hunters/Paleblood/pull/496)
  (closed without merge): compressed BC1/BC4 uploads must not use an invalid
  `vkCmdClearColorImage`. Track as a potential regression gate, not as an
  incorporated fix.

Other donor families already tracked: `Kalmarv/fromsoft-formats`,
`ividyon/WitchyBND`, `Meowmaritus/SoulsAssetPipeline`, `vawser/Smithbox`,
`Astrr00/BloodbornePC`, `droogie/bbhost`, shadPS4 variants and original
Bloodborne/DS3 resource format tools. The code in V363 is independently
implemented as a bounded glue layer; **do not copy upstream code without
per-file license and provenance checks**.

## Verification gates and critical limitations

The V363 test is a real multi-stage program with zlib, actual C parsers and
synthetic resources; a green CI validates exactly that. It does **not** prove
that every original Bloodborne resource can load, that a character model
renders, or that this is a source port of gameplay logic.

The decoded-archive scratch can be as large as the bound permitted by V360
(512 MiB maximum uncompressed) and is supplied/owned by the caller. This
module does not add an async scheduler, cache eviction, decompressed-resource
hashes or GPU lifetime management. Do not claim reduced RAM usage or lower
frame times without measurements from representative game scenes.

## Next milestone

V364 should produce renderer-neutral, validated GPU staging descriptors from
FLVER face sets and vertex buffers without copying or interpreting untrusted
indices on the GPU. It should manage source lifetimes, strip/restart semantics,
layout precision and bounded cache budgets. In parallel, prioritize the much
larger remaining task: **whole-game native Windows AOT/source reconstruction,
import/callback closure and first complete offline gameplay**, without a
runtime PS4 guest ELF/interpreter, followed by sound/physics/save/online.

No Fornex server, original game resources, gameplay saves, existing playable
BBPort or Ultimate Yharnam Together installation was modified by this work.
