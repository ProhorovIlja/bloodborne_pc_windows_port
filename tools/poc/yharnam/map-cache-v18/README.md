# V18 Bounded CPU Map Cache and Stop-Aware Worker

Pinned upstream: `lKaniel/bloodborne-server@77e350743a7cb4524cfcc1782fb6e3af64e25b15`, file `bbport/gpu/shim/bbport_map_charts.cpp`.

**Observed source issues:** the global `ready` and `ready_meshes` caches retained each visited map indefinitely, while background `Work()` was an immortal detached thread accessing the global cache and queue at shutdown.

**V18 source changes:** adds a 384 MiB soft-limit LRU for cache-owned CPU maps/meshes (active UI/GPU consumer `shared_ptr` references are not invalidated); ensures evicted entries are re-queueable using `asked.erase()`; protects active map queries with touch; replaces the detached thread with a C++20 `std::jthread` and interruptible `condition_variable_any` wait; logs and quarantines ordinary exceptions in map preparation. Does not alter gameplay map rendering or server state.

**Important limitations:** this is an ownership limit for the internal CPU chart cache, **not a cap on the whole process, GPU VRAM, active map pictures, or shader caches**. One large entry can exceed the soft limit. At graceful exit, `jthread` must wait for any ongoing expensive map generation to finish, so Quit to Desktop may be delayed while generating a new area. A future cancellation-aware map renderer may be needed. Reusing maps from disk avoids costly regeneration after LRU eviction.

**Tests:** `python -m unittest discover -s tools/poc/yharnam/map-cache-v18 -p 'test_*.py' -v`; `cmake -S tools/poc/yharnam/map-cache-v18 -B build && cmake --build build && ctest --test-dir build --output-on-failure`. A separate C++20 stop-token smoke test is included. Atomic unified source composer integration included after V17. True Windows game integration and two-PC map stress tests are still pending.
