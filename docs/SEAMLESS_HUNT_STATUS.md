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
