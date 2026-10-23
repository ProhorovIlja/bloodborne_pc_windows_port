# Seamless Hunt V18–V19: native map reliability audit

Pinned upstream: lKaniel/bloodborne-server commit 77e350743a7cb4524cfcc1782fb6e3af64e25b15.
Branch: feature/yharnam-dedicated-server-poc.
Status: SOURCE PATCHES COMPOSED. Full Windows game has NOT been compiled or runtime verified.

## Confirmed problems

* bbport_map_charts.cpp caches finished CPU charts and 3D meshes in global ready and ready_meshes without eviction, retaining RAM as more areas are visited.
* Its detached background Work thread loops indefinitely against global mutex, queues and caches, risking a race during normal process shutdown.
* bbport_map_art.cpp accepts corrupted .bbmap/.bbmesh dimension headers that could allocate hundreds of megabytes or multiple gigabytes, and archive entry offset+size could overflow.
* This is not proof that the player's observed VRAM leak or a particular map crash originates in these paths; GPU texture lifetime and crashes require separate profiling.

## Changes

V18: a 384 MiB SOFT shared CPU map and mesh cache budget with LRU eviction; active consumers continue owning their shared_ptr objects; evicted keys become re-queueable and disk cache remains reusable. A stop-aware C++20 jthread replaces the detached infinite worker, and catches ordinary map processing exceptions. Graceful shutdown might wait for a long map bake, since the renderer is not cancellation-aware internally.

V19: bounding cached 2D chart pixels at 48M, floor cells at 12M and uncompressed mesh data at 512 MiB, validating scale and floor dimensions, avoiding empty memcpy and checking collision archive ranges without overflow. Corrupt caches are rejected and can be regenerated.

## Evidence

Local isolated source tests: V18 Python 3/3, V19 Python 4/4. Both V18 C++20 cache/stop-token test executables compiled with g++ -Werror and passed. Upstream anchor counts were verified against pinned source. Changes integrated in unified-v9/compose_sources.py after V17. Integration fixtures and a GitHub Actions workflow have been updated, but no successful Actions run or full Windows game build on this branch has been observed.

## Remaining work

Build the actual Windows game, test opening maps and 3D views on two machines, validate corrupt cache fallback and long-running memory profiles, investigate renderer VRAM lifetime, and make map generation cooperatively cancellable for prompt shutdown. Production CLS/Fornex services unchanged.

Source files:
- tools/poc/yharnam/map-cache-v18/
- tools/poc/yharnam/map-data-v19/
- tools/poc/yharnam/unified-v9/compose_sources.py

GPL-2.0-or-later compatible with upstream.
