# Native V361 — BND4 index for a strict no-EBOOT Windows resource path

Date: 2026-11-11
Base: Native V360 `feature/native-v360-stream-dcx-verification-20261111`
Head: `feature/native-v361-safe-bnd4-index-20261111`

## User goal

Build an eventual standalone `Bloodborne.exe` on Windows with no PS4
eboot/ELF payload, guest interpreter/JIT, Orbis runtime or console GPU
command translation. The source-first game AOT/native engine remains the
critical path; this commit addresses one authentic asset-engine prerequisite.

## Concrete source evidence (private; no game bytes published)

The user's private Drive has both owned Bloodborne CUSA03173 v1.09 and
Dark Souls III PC unpacked resource folders. Two small, private character
resource containers were read *without writing any source bytes to GitHub*
and decompressed privately:

| Game | Source resource | DCX compressed | decoded BND | BND files | extension | data content |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Bloodborne | `c9010.chrbnd.dcx` | 349 B | 816 B | 1 | `extended=0` | FLVER |
| Dark Souls III | `c6281.chrbnd.dcx` | 2,528 B | 6,192 B | 1 | `extended=4` | FLVER |

Both have the little-endian `BND4` header, 0x40-byte main header,
0x24-byte file records, raw format byte `0x74`, UTF-16LE filenames,
and 64-bit stored/uncompressed sizes. The actual DS3 example contains
two hash buckets; its extended header contains the hash table at
offset 200, a hashes section at offset 232, and exactly one file
reference. Original Bloodborne sample has no hash table. These are
the **two verified format variants**, not proof all binders work.

The reference layout was compared with public
`JKAnderson/SoulsFormats` `BND4.cs`, `BinderFileHeader.cs`,
`Binder.cs` and `BinderHashTable.cs`. New C implementation
uses explicit bounds and independently written control flow. Third-party
licensing/provenance must be checked before any code is copied.

## Implemented

`native_bnd4_index_v361.{h,c}` adds an immutable, narrow, allocation-free
index probe on caller-owned decoded resource memory. It:
- Rejects unknown endianness, binder format and record size.
- Checks entry counts, per-record sizes, data offsets and overflow.
- Rejects record/payload overlaps with BND header region.
- Verifies names are UTF16LE NUL-terminated *before* the hash table when
  `extended=4` (or before header end when `extended=0`).
- Checks extended hash header, group bounds and referenced file indices,
  while refusing unsupported variants.
- Exposes a constant-time file-index lookup after one O(file_count +
  header bytes) validation; does not copy, decompress or execute entries.
- Keeps compressed entry content as opaque bytes. This code is **not**
  a generic loader and does not open arbitrary filesystem paths.

`test_native_bnd4_index_v361.c` uses only invented synthetic data,
including both extended modes, stored/compressed file flags, invalid
offsets, truncation, counters, malformed names, invalid hash
descriptors, and names running into hash table. CI compiles and
executes under Ubuntu (GCC and Clang) and Windows (clang-cl).

## What V361 does not do

It does not integrate an actual game asset manager, FLVER geometry
decoder, character animation or texture system, full static
recompilation, standalone game boot, offline gameplay or online
multiplayer. The older BBPort guest-code loader is still separate.
Neither private game resource nor decrypted game executable was
committed, redistributed, logged or exported.

## Next independent Windows-native milestones

1. Run privacy-preserving native BND4 parser checks on multiple owned
   binder variants; add bounded validation for required versions and
   compression flags only when verified.
2. Implement FLVER metadata/mesh format parser, deterministic asset
   handling and GPU upload ownership with small fixtures.
3. Close the full original-game AOT code path and native Win64
   import/callback boundary without a PS4 guest CPU. A synthetic AOT
   or an index parser alone cannot establish a native Bloodborne.exe.
4. Implement render/physics/event/AI/audio/save pipeline and measure
   offline game play on Windows hardware.
5. Add matchmaking/online, networking performance, settings, graphics
   enhancements and gameplay features only after reliable offline play.

Production Fornex, playable BBPort, Ultimate Yharnam Together and
real user saves are intentionally unchanged.
