# V19 Map Data Input Bounds

Pinned source: `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`, `bbport/gpu/shim/bbport_map_art.cpp`.

Observed correctness failures:

* Persisted BBMAP9 charts allow 8192² pixels, allocating 256 MiB for RGBA alone, and 8192² floor cells would allocate more than 2 GiB across decompression plus arrays.
* BBMESH1 accepts a stored uncompressed length up to 2 GiB before allocating memory.
* Collision archive offset checks use `entry.offset + entry.size`, which can wrap around for corrupt headers.
* Zero-sized floor arrays were passed into `std::memcpy`, which is better avoided entirely.

**V19** bounds RGBA to 48M pixels (192 MiB, above the built-in 6144² map generator's needs), floor cells to 12 Mi cells with geometry-consistent dimensions, mesh decompression to 512 MiB, rejects non-finite PPM, uses overflow-safe archive range checks and skips empty memcpy. Invalid cached maps are rejected and can be regenerated normally, never modified in place. No changes to game saves, network protocol or rendering quality. Uses pinned source anchors, not binary offsets.

Unit tests: `python -m unittest discover -s tools/poc/yharnam/map-data-v19 -v`. Full Windows runtime and malformed-file fuzz campaign not yet completed. GPL-2.0-or-later compatible with upstream.
