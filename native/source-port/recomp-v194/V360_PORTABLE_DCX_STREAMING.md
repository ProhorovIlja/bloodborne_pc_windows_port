# Native V360 — Portable, bounded Bloodborne/DS3 DCX_DFLT streaming

Date: 2026-11-11
Branch: `feature/native-v360-stream-dcx-verification-20261111`
Base: `feature/native-bulk-9955-fde-aot-v193-20261101`

## Scope

This is a **small real asset-engine subsystem**, not a game launch, gameplay,
network implementation or complete no-EBOOT port. It makes the existing native
Win32 DCX resource reader (`native_win_dcx_stream_v359.c`) call a portable,
testable zlib decoding core instead of duplicating the Deflate state machine.

- `native_dcx_dflt_stream_core_v360.{h,c}` takes an exact positional-read
  callback, a bounded file size and a caller-supplied output buffer.
- The existing Win32 owner-owned asset file/root containment checks remain in
  `native_win_asset_fs_v351.c`. The Win32 bridge requires exact byte reads
  and closes its file handle on both success and failure.
- Header parsing stays in the existing V354 decoder. It accepts only the
  supported DFLT envelope and refuses unsupported codecs and unbounded
  expansion (256 MiB compressed, 512 MiB uncompressed, ratio limit 256:1).
- Core reads in 64 KiB compressed chunks. It accepts no more than 15 trailing
  zero-alignment bytes, exactly one zlib member, matching advertised lengths,
  full input consumption and valid Adler-32.
- On any failed read / truncated stream / zlib error, returns failure and
  sets `*written=0`. Output memory may contain partial unverified content;
  callers must never use it after a failed return.
- No original game resources, EBOOT, ELF, keys, saves, addresses, or encrypted
  artifacts are committed or uploaded. Tests use deterministic synthetic DCX.

## Regression coverage

`test_native_dcx_dflt_stream_core_v360.c` exercises real zlib compression,
three input blocks, zero and nonzero trailing bytes, short output capacity,
truncation, checksum tampering, bad envelope, wrong declared sizes, read
failure on the header and on all three compressed chunks, and recovery of
the valid fixture after corruptions. The original V355 test also compiles
and exercises the Win32 actual filesystem path.

GitHub Actions `native-v360-dcx-stream-core.yml` builds the pinned public
zlib 1.3.1 source and executes both test suites under Windows/MSVC-compatible
clang-cl and Linux/Clang. A successful CI job would validate this data-path
implementation, **not** establish game-derived compatibility, frame-time
improvement or offline gameplay.

## Strict native source-port track

The real goal remains `NO_EBOOT_WINDOWS_NATIVE_TARGET.md`: an independent
Windows game executable compiled from source-level/recompiled game logic, a
fully native resource/render/physics/input/audio/save engine, and eventually
online. Game assets may be read from an owned install but runtime gameplay
cannot execute or map a PS4 executable or route through an Orbis guest.

The other parallel port family (deadinside28, Mrsuss60, Supermedo, visy,
BBHost, shadPS4, Lantern Engine) is valuable for observed rendering behavior,
resource format rules, gameplay bugs and PC controls; its executable loader
and PS4 GNM/HLE paths are **not** to be silently treated as a source port.

Additional reference tracks for later code comparison:
- `bloodborne-native/bloodborne-recomp`: AOT/x86 state and function CFG;
  unresolved compatibility callbacks remain a blocker.
- `Yharnam-Hunters/Paleblood`: independently verified function-by-function
  source reconstruction and own runtime; it explicitly does not run the game.
- `ividyon/WitchyBND` and `SoulsFormats`: reference FromSoftware resource
  formats. Any code reuse requires license and provenance review.
- Owner-provided CUSA03173 and Dark Souls III folders in private Drive:
  analyze **metadata and tiny bounded fixtures privately**, never commit
  game-owned bytes or embed them in CI.

## Remaining milestones (not complete)

1. Privately sample real Bloodborne and DS3 DCX variants to confirm the
   narrow DFLT header assumptions. Refuse unknown codecs explicitly.
2. Integrate native archive readers, async resource scheduling, memory
   budgets, decompressed hash validation and cache ownership; benchmark on
   owner hardware (not assumed).
3. Full-game original-code AOT, native import closure without callbacks,
   real scene loading, window and independent PC graphics, then offline
   gameplay / save correctness.
4. Only after reliable offline play: co-op, network, gameplay extras,
   Reflex/upscaling and performance tuning with A/B measurements.

This work does **not** touch Fornex, any live player saves, the existing
Yharnam Together production client, or the current playable BBPort release.
