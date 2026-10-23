# V17 Conservative Vulkan Texture Collector Guard

Pinned source: `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`, file `bbport/gpu/shadps4/video_core/texture_cache/texture_cache.cpp`.

This is a selective adaptation of image-binding safety from Mrsuss60/bloodborne_pc_windows_port commit 89f05218 and visy/bloodborne_pc_windows_port. Prevent GC eviction of images with active render/read bindings, presentation surfaces, and scene proxies. Default behavior does NOT alter the pressure thresholds, quota, idle time or existing writeback. This aims to reduce artifacts and invalid GPU resource retirement without making cache thrash worse.

Additional candidate based on Mrsuss60 PR #89 (0144b5c): stale depth/stencil recovery. Intentionally OFF by default pending actual GPU runtime validation. Opt-in via process environment `SH_GC_RECLAIM_DEPTH=1` prior to launching the experimental game. Do not enable by default for users and never use it on a production build without multi-area/perf tests.

Tests: `python -m unittest discover -s tools/poc/yharnam/gc-safety-v17 -v`.
Runtime-tested with two PCs: NO. Windows game compiled: NO. Test-server or CLS production changed: NO.
