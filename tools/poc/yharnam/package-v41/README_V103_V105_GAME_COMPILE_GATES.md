# V103–V105: compile the actual native game first, retain failing logs, avoid queue congestion

Development only, DRAFT PR20. Original Yharnam Together native game source pinned at `77e350743a7cb4524cfcc1782fb6e3af64e25b15`. No changes to live Fornex/master, user accounts, saves, third-party production servers, or game Direct UDP routing.

## V103: genuine native game C++ compilation before GPU

The original `bbport/gpu/CMakeLists.txt` has a real static `bbnet` target. Its `BBCOOP_SOURCES` includes the native `bloodborne_re.cpp`, `bloodborne_party.cpp`, `bloodborne_party_death.cpp`, and `bloodborne_flags_store.cpp` files updated by V97, V98 and V99. `bbgpu` depends on `bbnet`. Before V103, the native Windows Ninja build requested all GPU/game targets together, so gameplay C++ failures could be buried under many minutes of GPU shader and FidelityFX compilation.

`patch_bbnet_first_v103.py` source-checks the pinned original `bbport/build.sh` and inserts `ninja -C out/gpu bbnet > out/bbnet-build.log 2>&1` first, and refuses the graphics build if game/net C++ fails. The existing full GPU targets still build normally once `bbnet` succeeds.

The narrowly scoped `shyt-v103-game-bbnet-before-gpu.yml` verifies the **actual original source and CMake build-target order**, separately on Windows and Ubuntu. **A passing source test is NOT a compiled bbnet library or a bootable native client.** The full `shyt-v63-native-game-candidate.yml` job must provide that stronger evidence.

## V104: diagnose both game and GPU compiler errors

The previous V102 watchdog checked only `out/gpu-build.log`. V103 introduces a separate `out/bbnet-build.log`. V104 checks BOTH logs for decisive compiler/Ninja failure records every 30 seconds and immediately reports the offending log. It excludes normal warnings and packages both logs into a short-retention **internal failure artifact**, not a public game download. Added a cross-platform regression with injected bbnet/GPU compiler errors and benign warnings.

## V105: coalesce obsolete pending full native builds

The top-level full native candidate workflow now has:

```yaml
concurrency:
  group: shyt-v105-native-full-game-${{ github.ref }}
  cancel-in-progress: false
```

Successive commits to the same branch can replace older **pending** full-build requests with the latest request, without cancelling the **currently running** multi-hour native compiler job. This reduces wasted Windows runner time and retains progress on existing long builds. The grouped concurrency applies only to subsequent workflow runs that use this version of the workflow; it does not retroactively cancel older runs already active before V105.

## Strict release gate

Wait for a *completed successful* full native Windows compile, link, three runnable tools and internal ZIP/hash integrity check. Even that does not by itself demonstrate real Bloodborne game boot, save compatibility, Vulkan stability, seamless co-op or Direct P2P. Those require separate Windows runtime testing with legitimate game assets and two actual players.

No working EXE/ZIP, P2P gameplay route, two-PC test or claimed CPU/bandwidth reduction is established by V103–V105 alone.
