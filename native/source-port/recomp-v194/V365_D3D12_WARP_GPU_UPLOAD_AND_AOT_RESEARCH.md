# Native V365 — real D3D12 staging, GPU transfer, fence ownership, WARP readback

Date: 2026-11-11 (Europe/Stockholm). Repository: `ProhorovIlja/bloodborne_pc_windows_port`.
Base: `feature/native-v364-renderer-neutral-gpu-staging-20261111` (PR #94).
Branch: `feature/native-v365-d3d12-warp-upload-20261111`.

## Contract: no runtime PS4 executable

V365 is a Windows-native **rendering-resource backend** for a future independently
compiled `Bloodborne.exe`. It neither loads nor executes the original PS4 EBOOT,
ELF, eboot-based HLE or interpreter. It consumes V363/V364 validated, caller-owned
FLVER2 bytes, **not** game code. The overall game still does **not** launch from
our strict no-EBOOT source-port track, and nothing here is a full renderer.

Using a legally owned executable as *build-time input* for a static reconstruction
is different from mapping that executable as a **runtime payload**. The requested
final port must work without the runtime PS4 executable; a build-time
recompiler must also prove all executable control-flow and imports are closed.

## New code

- `native_d3d12_flver_upload_v365.{h,cpp}` links to the existing V362
  FLVER2 validator and V364 GPU staging plan. It uses a Windows D3D12 DIRECT
  command queue (never a PS4 GPU command stream).
- It revalidates the source, applies an independent **256 MiB hard limit** and
  the caller's more restrictive staging budget, bounds the vertex/index view
  count (4,096 each) and draw descriptors (131,072).
- Allocates a CPU-mappable D3D12 `UPLOAD` heap and a GPU `DEFAULT` resource.
  Copies each source span into the mapped upload heap, padding the unused bytes
  deterministically. No original game data is committed or logged.
- Records `CopyBufferRegion`, transitions the destination from `COPY_DEST` to
  `VERTEX_AND_CONSTANT_BUFFER | INDEX_BUFFER`, submits the list to an actual
  Direct3D 12 queue, and signals a fence.
- Returns GPU vertex/index views and draw descriptors; the caller can use
  them only after the fence reports completion. Pending ticket keeps upload
  resource, command list and allocator alive; timeout does **not** discard
  in-flight staging. Destruction of a still-pending ticket can wait, so
  retirement belongs off the latency-critical render thread.
- Explicitly rejects a mismatched D3D12 device/queue pair. A fence completion
  value of `UINT64_MAX` is device removal, not success; GPU views and their
  backing object are invalidated and a failure is reported.
- Valid geometry with zero GPU bytes makes no empty D3D12 buffer.

## Evidence: synthetic real GPU execution

`.github/workflows/native-v365-d3d12-warp.yml` compiles the C FLVER/V364
contract code under Windows clang-cl, the C++ D3D12 backend, and a native
Windows unit executable. It obtains Microsoft's `IDXGIFactory4::EnumWarpAdapter`
software D3D12 device, submits GPU copy commands, waits for the fence, reads
back through a `READBACK` resource, and checks that **all bytes** equal the
original invented vertex and index data. It tests short budget, wrong queue
kind, damaged source indices, immutable resource ownership, and an empty model.

Linux builds and runs the inherited V364 source-only contracts with Clang
and AddressSanitizer/UndefinedBehaviorSanitizer. Linux never runs D3D12.

**Proof boundary:** WARP is a software implementation of D3D12, not a dedicated
NVIDIA/AMD/Intel GPU. This is **not a measured hardware framerate, zero
stutter, full FLVER render, shadow/material system, or online game**. The
public tests use synthetic FLVER data; testing a complete V365 path on private
original game models remains a separate acceptance gate.

## Upstream research: cross-repository / PR candidates

Repository and PR searches included Bloodborne and related FromSoftware
projects, plus unrelated Windows D3D12 sample and allocator implementations.
This is a targeted search, not a literal exhaustive read of all GitHub.
These findings are *research leads*; no upstream source code was copied.

1. [Microsoft DirectX-Graphics-Samples](https://github.com/microsoft/DirectX-Graphics-Samples):
   reference patterns for Win32 GPU command list lifetime, WARP testing,
   resource states and shader pipeline. Use docs and tests first.
2. [GPUOpen D3D12MemoryAllocator](https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator):
   MIT library supporting GPU heap suballocation and budget-aware pooling.
   Future V366 should measure it against per-model `CreateCommittedResource`
   allocations and check license when actually integrated.
3. [Paleblood PR #595](https://github.com/Yharnam-Hunters/Paleblood/pull/595),
   merged 2026-11-11: its Vulkan renderer moved completion work off the
   submitting thread, using ring slots, timeline-semaphore tickets and
   deferred completion writes. Its performance measurements are for a
   different Vulkan renderer and **not** transferred to our D3D12 backend.
4. [Paleblood PR #463](https://github.com/Yharnam-Hunters/Paleblood/pull/463),
   merged: batched draws instead of queue-wait per draw. Useful for V366
   frame scheduling and ring ownership, not itself a D3D12 drop-in patch.
5. [droogie/bbhost PR #204](https://github.com/droogie/bbhost/pull/204),
   merged: guided render jobs, low-VRAM import retirement, deferred upload
   waits and occlusion correctness. Depends on its PS4-ELF host runtime;
   relevant behavior and regression tests can be reproduced independently.
6. [droogie/bbhost PR #73](https://github.com/droogie/bbhost/pull/73),
   open: Reflex/FSR/DLSS and pacing integration candidates. **Do not**
   claim they are included in V365, or verified on our GPU.
7. [Astrr00/BloodbornePC](https://github.com/Astrr00/BloodbornePC):
   meaningful Windows static-recomp work, but documented runtime `bbgame`
   still loads the game dump's executable for segments and relocations. It
   does not satisfy the requested **zero runtime ELF** final criterion yet.
8. [bloodborne-native/bloodborne-recomp](https://github.com/bloodborne-native/bloodborne-recomp):
   useful AOT instruction coverage, function table and local SIMD state;
   documented interpreter fallback remains a blocker for a fully
   independent game. See merged PRs #7, #8, #10 and #11.
9. [Yharnam-Hunters/Paleblood](https://github.com/Yharnam-Hunters/Paleblood):
   source reconstruction and engine-level renderer evidence, but its
   published verified-function percentage shows why source parity remains
   a far larger milestone than resource loading alone.

Official API rules cross-checked: Microsoft Learn `Uploading different types
of resources`, `Using Resource Barriers`, `EnumWarpAdapter`, `Fence-Based
Resource Management`, and `ID3D12Fence::GetCompletedValue`.

## Next evidence gates (not implemented in V365)

1. GPU integration with V360→V364 on **private owner-provided original
   assets**, plus render-to-target smoke with a portable test shader. Keep
   extracted copyrighted bytes out of GitHub and public CI.
2. Test NVIDIA/AMD/Intel feature levels, residency, low-VRAM pressure,
   GPU reset/device lost, blocking destructors, multiple in-flight uploads,
   cache eviction and GPU buffer retirement under measured fence watermarks.
3. Replace one-buffer-per-model allocations with a bounded upload ring and
   batched draw/resource submissions only where benchmarks justify it.
4. **Critical path:** reconstruct all original game logic into target-owned
   Win64 C/C++ without runtime PS4 ELF, close imports/callbacks and guest
   interpreter fallbacks; then offline native gameplay, saves, graphics,
   audio/physics, and later online/matchmaking/optimization.

Never change Fornex, player saves, private original game files, or the current
playable BBPort/Yharnam Together installation as part of these tests.
