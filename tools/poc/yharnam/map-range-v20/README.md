# V20: Overflow-safe game archive range reads

Pinned upstream: lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15.

## Bug
bbport/gpu/shim/bbport_map_charts.cpp contained two callers that created a vector of an archive-supplied byte length before checking whether the referenced region existed in the file. Malformed ranges, overflowing offsets and truncation could lead to extreme RAM allocations, exceptions, or partial files passed into the decoder. These paths run both in live map loading and in the map precomputation entry point.

## Fix
The single `sh_map_range_io.hpp` implementation performs all checks before allocation:
- refuses zero size and requests over 512 MiB per archive chunk;
- refuses offsets/lengths exceeding the stream API's signed integer range;
- opens the actual file at EOF and verifies size, then checks `offset <= file_size` and `length <= file_size - offset` without overflow;
- reads exactly the requested amount and rejects any truncated read.

`patch_map_range.py` replaces both readers and fails closed when pinned source anchors are different. The unified source compositor intentionally applies V20 **after V18** to the same file, retaining its LRU cache and stoppable worker. The 512 MiB single-chunk guard might require adjustment for unusual very-large modded assets; do not silently raise it without measuring normal chunk sizes.

## V17 follow-up from this audit
The original V17 GC patch used `image.scene_proxy` as an unconditional keep-alive. SceneTargets::SetSize() clears entries without clearing that flag, so this could permanently pin old images and aggravate long-session VRAM accumulation. V17 has been corrected to protect currently bound/target images and presentation surfaces only, retaining the original GC age/writeback policy. Full Windows GPU rendering regression tests are still necessary.

## Tests and evidence
- V20 4 Python unit tests passed.
- Native C++20 stream-range unit test passed, including 169 possible short-range input combinations.
- Clang/GCC-compatible code locally built with GCC 14; UndefinedBehaviorSanitizer test passed.
- Pinned source had exactly one anchor for each original reader and include insertion.
- V15–V20 isolated Python tests passed (25 tests total), and V18 2 C++20 tests passed.
- Full Windows Bloodborne client build, multiplayer, long VRAM sessions and automated GitHub Actions **not verified**.
- Neither production CLS nor Fornex service was touched.

How to test:
```
python -m unittest discover -s tools/poc/yharnam/map-range-v20 -p 'test_patch_*.py' -v
cmake -S tools/poc/yharnam/map-range-v20 -B build/map-range-v20
cmake --build build/map-range-v20
ctest --test-dir build/map-range-v20 --output-on-failure
```

All changes are source only. No PS4 game content or executable distributed.
