# BBSC legacy NP bridge for the native Windows runtime — implementation checkpoint

**Date:** 2026-10-22. **Status:** genuine native loader/ABI source wiring, **not** working online gameplay.
**Never expose this dev-only flag in the public launcher until bbnet20.dll is compiled, tested, versioned and audited.**

## Implemented in this branch

- `src/runtime_legacy_net.c`, `src/runtime_legacy_net.h`, `src/runtime_legacy_host.h`, `src/runtime_legacy_policy.c/h` provide a gated **Windows DLL adapter**, with the same v2 `BbNetHost` layout as deadinside28/bloodborne_pc `gpu/bbnet/bbnet.h`.
- A developer may request `BB_LEGACY_NET=1`, **only while BB_PARTY is unset**; visy's encrypted BBP3 party wins and is never mixed with shadNet game-network frames. The module is not initialized in CPU-only boot or without a known game identity.
- The native runtime looks for **`gpu/bbnet20.dll` adjacent to `bbport.exe`**, via an absolute executable-relative path with Windows restricted DLL search. No arbitrary path supplied from an environment variable.
- A DLL must export `bbnet_init` and `bbnet_resolve`; optional lifecycle exports are `bbnet_image_mapped`, `bbnet_image_ready`, `bbnet_start`. Initialization receives guest-safe tracked thread spawn/join/exit, game identity and mapped-memory checks. If DLL loading/ABI negotiation fails, network imports use the original offline stubs rather than terminating the game.
- The map hook is called after game relocation and before image patches; the ready hook is called after native game patch application while code is still writable; the start hook is called after game linked-module TLS initialization and before original entry. Note that ordering relative to any future BBSC mod DLL hooks must still be verified.
- Only network/NP/HTTP/SSL imports may be delegated. Trophy, commerce, profile, score and party dialogs remain local; ordinary video/audio/graphics remain unchanged.
- `tests/test_legacy_online_policy.c` checks mode conflict, network import allowlist, and exact 72-byte x64 ABI struct layout. The GitHub native-client-checks workflow runs these tests on Ubuntu and Windows; the Windows **full engine** workflow is separately triggered and must actually finish successfully before calling this compiled.

## Not implemented yet (do not mark green)

1. **No Windows `bbnet20.dll`** from the pinned Linux sources currently exists in the fork. The hosted source-staging CI only inventories the source tree and checks its SHA/commit/license, not a Windows build.
2. The upstream deadinside28 module was derived from shadPS4 v0.20 and a prior BBSC tree. The published docs predate CLS **BBSC 0.0.2** in-game fixes. Match 0.0.2 NP/summon/signaling/scene behavior and maintain backwards compatibility; preserve upstream notices.
3. Audit all Windows system dependencies: guest hooks/trampolines, Vulkan vs Windows guest memory permissions, TLS/GS base, `dlsym` alternatives, host callbacks, networking sockets, Protobuf, Win32 UI substitutes, shadNet account persistence, SSL and Win64 export macros. The native Windows port must compile and pass source and binary ABI tests.
4. **Actual login** must securely bind the player's game session/account to Seamless Hunt; the launcher currently only does a temporary unencrypted TCP verification. Do not expose it as secure sign-in, auto-store passwords, or send plaintext credentials through an allegedly protected gateway.
5. Both directions of bell, room, actor replication and host selection with **unmodified** CLS 0.0.2 shadPS4 and BBPort must work in real sessions. ShadNet login and TCP server reachability are necessary, never sufficient.
6. Test wrong/passwordless password combinations, wrong server, all summon types, Nat/CGNAT, IPv6, relay/direct, death/respawn/lamps, stage loads, PvP, save corruption recovery, unresponsive backend and long sessions. Benchmark connection time and packet overhead. No forced public-server changes or disruption to visy party.

## Compilation and checks

The new adapter .c is automatically picked up by the existing CMake `src/runtime*.c` glob. It is inert by default, needs no extra DLL or packages for a normal solo/party build and on non-Windows targets compiles as no-op. A future adapted `gpu/bbnet20.dll` lives beside the native `gpu/bbgpu.dll` (one exe directory below the GPU folder), not inside the retail game directory.

```sh
cc -std=c11 -Wall -Wextra -Werror tests/test_legacy_online_policy.c src/runtime_legacy_policy.c -o legacy-online-policy
./legacy-online-policy
```

**Quality rules:** A successful test of `legacy_net_online_symbol` is **not** a successful engine compilation; a successful engine compilation is **not** a BBSC game session. The release stays blocked until all of those progressively pass, and until the single cumulative user-ready build is produced.

## Next implementation slice

Port upstream `gpu/bbnet20` to Win64 as a separately linked `bbnet20.dll` with strict imports and the shared host ABI, initially without gameplay. Add a CI dynamic-load smoke fixture, then guest hook compatibility, then secure account/signaling and actual room join. Integrate current CLS 0.0.2 gameplay behavior, perform Windows engine compilation, real cross-client acceptance and finally enable the launcher option.

References: `docs/SEAMLESS_HUNT_PRODUCT_CONTRACT.md`, `docs/LOCALIZATION_AFTER_FEATURE_FREEZE.md`, `docs/SEAMLESS_HUNT_ECOSYSTEM_AUDIT_2026-10-22.md`.
