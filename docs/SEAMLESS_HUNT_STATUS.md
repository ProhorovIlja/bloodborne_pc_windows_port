# Seamless Hunt native client: engineering status (2026-10-22)

> **Canonical product scope and owner-ready release gates:** [SEAMLESS_HUNT_PRODUCT_CONTRACT.md](SEAMLESS_HUNT_PRODUCT_CONTRACT.md). Internal source/CI iterations are not owner-facing acceptance builds. See the contract for the complete native client, online, launcher, mods, QoL, security and performance requirements.


One codebase: this visy-based native Windows port. Do not create other client forks or replace its existing multiplayer transport without evidence.

## Validated baseline
- Fork branch: `feature/seamless-hunt`. The native-client-checks workflow passed.
- Existing port already has party P2P, NAT traversal, route selection, member-relay fallback, save safety, built-in launcher, graphics options and automated party tests. Preserve these.
- User-provided Windows handoff contains custom shadPS4/BBSC networking and Qt launcher sources, plus earlier Awaken experiments. Its snapshot is partial, not a standalone build tree.
- User-provided Seamless Hunt server handoff contains a candidate shadNet tree and native relay packages.
- Python GameServer and BBHost service payloads from those archives match their deployed production file hashes, confirmed with a read-only VPS inventory.
- Local offline build-and-test scripts for Native TCP Relay v15 and Native UDP Relay v17 completed successfully. UDP rebuilt binary matches package binary by SHA-256.
- Exact source commit for the deployed shadNet binary remains **unverified**. Offline tests are not live multiplayer validation.

## Real Win64 BBSC transport compile and regression milestone (2026-10-22)

- **Confirmed:** experimental [native BBSC Windows module CI run 39810150080](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/39810150080) compiled **425/446** real C/C++/Protobuf objects from pinned `deadinside28` shadPS4/BBSC sources before a *specific Windows-only missing dependency*: `core/net/host_net.cpp` requires `wepoll.h`. This is no longer a conceptual ABI stub or independent native renderer; actual Windows shadNet/NP sources were compiling.
- **Fix committed:** pin the original BSD-licensed `shadps4-emu/ext-wepoll` repository at `d3bb81035304a0dc6a5ca48ebf0f8cee1fe269e4`, compile its real C implementation as a static library and link it into `bbnet20.dll` only in the **OFF-by-default candidate target**. Include its license in the pinned CI checkout; release packaging remains **unchanged** and excludes this unverified online module.
- Added `tests/test_wepoll_win.c` and a CI gate exercising real `127.0.0.1` UDP send/receive, `epoll_ctl`, `epoll_wait`, socket cleanup and readiness-event identity with the exact upstream `wepoll.c`; no external server or user credentials are used. The last workflow stage now checks **each** of the five real `bbnet_*` exports, rather than accepting a single matching export.
- **Improved runtime isolation:** once the user selects the functioning visy P2P transport, or disables `BB_BBSC`, even an already-loaded experimental DLL cannot run subsequent `image_mapped`, `image_ready` or `start` callbacks; Win64 mock DLL regression tests cover the post-load transition.
- Offline CI tests passed in the last confirmed `native-client-checks` run; the full new candidate DLL Windows linking, real gameplay, actual CLS 0.0.2 online interoperability and cross-host random joins **remain unverified until the relevant workflow completes and live game tests exist**. The baseline Windows engine independently built successfully before this change. No production server, save or account state was touched.

## Confirmed build milestone and safe integration gates (2026-10-22)

- **Verified:** GitHub Actions [Native Windows engine build run 39796354787](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/39796354787) completed **successfully** for source commit `77d71b7c18a275d16324e1f639bd9a4d11e220e7`. It built `bbport.exe`, passed the Windows party C++ checks, staged the portable Python 3.12/Tcl/Tk launcher, verified the release ZIP and successfully smoke-tested the **extracted** launcher in a Unicode path. It uploaded `seamless-hunt-native-windows-dev` (~171 MB archived artifact). This is the first independently confirmed *whole-toolchain* Windows build, **not** a game/crossplay proof.
- The next changes are not certified until their own full CI completes. Local simulator/unit tests and an old successful artifact must not be silently counted as live random-player compatibility.
- Source comparison includes original CLS BBSC 0.0.2, the native deadinside `bbnet20` module, and user-provided private Windows/server snapshots. The native module differs in four of five BBSC gameplay files from CLS 0.0.2: do not transplant or enable old scene/death/relay behavior without conflict checks.
- Real `bbnet20` candidate Windows CMake compiled dependencies and progressed to genuine vendored NP sources; found a missing shadPS4 logging-classes include path (fixed in `gpu/CMakeLists.txt`), and an upstream checkout line-ending mismatch in Windows game-memory adaptation (fixed with CRLF regression tests). **No native BBSC Windows DLL has yet been certified or placed into an owner-facing archive.**
- Runtime now requires **both** developer `BB_LEGACY_NET=1` and `BB_BBSC=1`, a valid Bloodborne 1.09 identity, and **no** visy party session before a real module can be loaded. Unrelated title, older Bloodborne version, missing DLL, and partial opt-in do not touch the working P2P route. `tests/test_seamless_hunt_dev_package.py` also asserts that even a freshly compiled, unverified `out/gpu/bbnet20.dll` is excluded from the portable package.
- Live Fornex, shadNet, GameServer, the account website, real player saves and the `master` branch remain untouched by these CI/source changes. Previously confirmed production service hashes are private and stay out of the public repo.

## Latest native build and cross-play engineering (2026-10-22)

- Normal native `bbport.exe` reached successful link in Windows CLANG64 CI. Windows party-tests initially hit an include-path collision between the repo's `VERSION` and libc++ `<version>`; their include paths were corrected. **A fully successful packed-and-unpacked Windows executable + launcher acceptance job is not yet independently verified.**
- **Real**, pinned deadinside `bbnet20` 0.20/shadNet/BBSC source is staged with third-party `cpp-httplib` MIT license and explicit Win64 changes. The first platform adaptations handle `__declspec(dllexport)`, Linux `setenv` vs Windows `_putenv_s`, `/proc/self/maps`/POSIX `mprotect` vs bounded guest-image `VirtualQuery`/`VirtualProtect`, and disable arbitrary Linux-only memory probing on Win64.
- Added a separate `Native BBSC Windows module candidate` workflow, gated behind OFF-by-default `BB_BBSC20_WINDOWS_CANDIDATE`, with Win64 Protobuf, OpenSSL, zlib, nlohmann-json, miniupnpc packages. It aims to **compile the real module**, unlike the existing mock-DLL load tests. Build status must be taken from live GitHub Actions, not this static status page.
- The legacy NP resolver now forwards otherwise-unrecognized **syntactically valid 11-character PS4 NID hashes** to the real module's own explicit symbol registry. Known non-network symbols continue using the unchanged runtime. This handles mismatched/extra upstream NP import maps without catching unrelated guest service symbols.
- This candidate is isolated from the public portable artifact, production VPS/shadNet and visy party runtime. **No live random-player connection is confirmed; no release-ready BBSC Windows DLL is certified.** No player-side testing requested.

## Engineering checkpoint (2026-10-22, BBSC NP/Windows bridge)

- The **optional** native Windows legacy NP/BBSC module entrypoint is now wired through `src/runtime_services.c` and `src/probe.c` (imports, mapped image, image patches, game-start). It is **off by default** and refuses to mix with `BB_PARTY`.
- `src/runtime_legacy_host.h` defines the original deadinside28 bbnet20 v2 72-byte host ABI; `runtime_thread.c` supplies tracked guest-thread spawn/join/exit rather than running guest code in arbitrary host threads. `src/runtime_legacy_policy.c` whitelists legacy network/NP/HTTP/SSL imports but leaves trophy/commerce/profile local. `tests/test_legacy_online_policy.c` verifies this.
- The optional loader searches only an executable-relative `out/gpu/bbnet20.dll`, never arbitrary current-directory or environment paths. A DLL absent/failed to initialize falls back to offline stubs. CPU-only boot doesn't start a network backend.
- **Still missing:** a compiled **Windows** `bbnet20.dll` (the pinned upstream sources are **Linux**), official CLS BBSC 0.0.2 sync, secure in-game Seamless Hunt account binding, live interoperability with unmodified BBSC shadPS4/BBPort users. The user-facing launcher does **not** enable this developer-only path. Under no circumstances describe the result as working crossplay.
- The full `Native Windows engine build` PR workflow now reports a separate engine build result, distinct from Python/UI/source tests. **A completed successful full engine build has not yet been independently verified in this checkpoint.**
- Launcher now has `Ctrl+F` search and an isolated low-latency graphics preset; Unicode search is regression-tested. Future translation is deferred by user choice: [LOCALIZATION_AFTER_FEATURE_FREEZE.md](LOCALIZATION_AFTER_FEATURE_FREEZE.md).
- See [BBSC_NATIVE_WINDOWS_ADAPTER.md](BBSC_NATIVE_WINDOWS_ADAPTER.md) for architecture, security, upstream pin and exact missing tasks. All owner-facing acceptance remains gated by [SEAMLESS_HUNT_PRODUCT_CONTRACT.md](SEAMLESS_HUNT_PRODUCT_CONTRACT.md).

## Next engineering target
1. Implement a **feature-gated**, optional Seamless Hunt account + session-discovery adapter using the current service contract. Do not expose credentials or send raw party secrets to logs.
2. Keep visy's direct P2P as the game transport. Seamless Hunt is discovery/authentication and possibly a carefully specified fallback, not a drop-in replacement for the party protocol.
3. Distinguish native-to-native play from old BBSC shadPS4 interoperability. A shared account/server alone cannot bridge incompatible game protocols.
4. Test password checking on every route, NAT failure, reconnection, recovery after death, and save consistency before enabling integration by default.
5. Afterwards evaluate Downed/Revive gameplay and graphics/VRAM/performance improvements from other GPL-compatible sources, measuring regressions.

## Safety and release discipline
- Do not change the live VPS or restart production services as part of source review.
- Never commit private server configs, accounts, logs, keys, game files, or uploaded private archives into this public repository.
- Keep upstream credits and all required GPL notices.
- Each build must identify its exact source revision and undergo Windows game tests on two physical PCs.
- Main/master should remain stable; develop only on `feature/seamless-hunt` until tested.

The detailed private source-inventory report was delivered as `SeamlessHunt-Source-Baseline-2026-10-22.md` in the user's chat. It is intentionally **not** copied here because it includes installed service fingerprints.
