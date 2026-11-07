# Seamless Hunt unified playable product: source triage, 2026-11-06

**Scope:** server + playable game client + launcher only. Native non-eboot
port deferred. Read-only source and CI work does not authorize a public
release, production Fornex changes, user game-file distribution, or use of
private Google Drive materials as public repository fixtures.

## Original Yharnam Together v1.4.0 (target gameplay baseline)

- Exact release SHA: `efa0ad265d840d9195e55db2e3216f46f7daedd0`.
  https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/releases/tag/v1.4.0
- Original `server/coop/coop.proto` declares protocol **8** and original
  `Envelope` fields: Welcome=2, Entries=5, SnapshotRequest=6, Snapshot=7,
  LobbyState=25, TeamStart=26. This remains the source of wire truth.
- Released team-of-five, launcher updater, public server/accounts/quick
  match and co-op gameplay fixes should be adopted *as a unit* when
  compatible with the chosen runtime. Never duplicate those completed
  features or mix release editions within the same party.
- Architecture deliberately uses a server relay for game packets, a server
  world log, and one reliable authenticated UDP link per game. A selective
  Direct P2P implementation is therefore NEW engineering, not an option
  exposed by v1.4.0. Reference:
  https://bloodborne.seamlesscoop.dev/docs/netcode
- Upstream **open** as reviewed this date:
  - https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/524
    Travel Together send/receive mutex inversion. Preserve its exact
    locking regression before merging a candidate.
  - https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/537
    Launcher 3D map does not refresh after co-op game-folder change.
  - https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/502
    Draft returning-game greeting/stream restart recovery.
  - https://github.com/Amanises-Yharnam-Together/BBSC-Yharnam-Together/pull/444
    Owner traffic load testing. Evaluate real CPU/bandwidth rather than
    treating a build as a performance benchmark.

## BBHost runtime/performance

- Existing pinned v0.2.24 plugin build is a **source-only** pilot. Its
  successful CI is not YT 1.09 in-game NetSync.
- v0.2.26 P2P send/receive sites moved after v0.2.24. Existing source-
  pinned V13/V19 overlays do not automatically apply to new upstream.
  No silent v0.2.26/0.2.27 version bump.
- https://github.com/droogie/bbhost/pull/213 is a **draft** v0.2.27
  Windows/low-VRAM performance candidate: test on target cards, OS,
  uncapped and 60-FPS modes, compare equal scene/hardware and VRAM.
- No GPU optimization may bypass authenticated gameplay packets or
  lower five-client deterministic correctness.

## NightwatchCoop as a network design comparison, NOT a YT binary

- https://github.com/vladtepes22/NightwatchCoop
- `engine/gpu/shim/net/party_udp.h`: direct guest-peer UDP path,
  two-way probe/ACK, fallback to a *host* relay, and a distinct relay
  framing/token contract (source blob `07e14a482cd36cb02f0902bade19c08ecb89fb12`).
- `engine/gpu/shim/party/party_nat.h`: explicit STUN-mapped NAT
  classification, CGNAT/double-NAT checks, UDP hole punching and
  forward/VPN fallbacks (source blob `c9064fee815f316e623950231986f4fa59e0aba6`).
- `engine/docs/party/network_robustness.md`: deterministic network
  simulator for loss/jitter/reorder/duplicates/outages and evidence that
  some prolonged outage/late-join cases needed resync retries.
- Its shared files use GPL-3.0-or-later; check license/attribution for
  any permitted adaptation. The Nightwatch peer protocol and YT
  server-authoritative room worlds are NOT wire-compatible. Reuse the
  *test and failover methodology* before considering any bounded code
  adaptation. No claim that Nightwatch eliminates Fornex traffic for YT.

## CLS gameplay and mod-safety candidates

- https://github.com/CLSAMG22/BBSC/pull/38: in-place fallen hunter
  revive, progress/cancel rules, boss wipe, HUD and animation hooks.
- https://github.com/CLSAMG22/BBSC/pull/22: guest position after boss
  kill versus unsafe far host lamp. Keep separate from DBNO.
- Before enabling a gameplay modification: verify exact YT v1.4.0
  hook/memory version and source-prologue, host-vs-guest semantics,
  reward idempotency, original game files, local save isolation, and
  five-hunter reproducibility.
- Private user game/mod/Drive materials must never be committed. Test
  scenarios may be described generically: guest hot-join/invisible
  remote actor, unknown role prompt, duplicate gift claims, conflicting
  XML patch offsets and shared HKS/event-script replacement.

## What V423 actually achieved (PR #86)

- Builds on original authenticated SHLK4/Noise-NK `CoopStream`,
  bounded V421 full Snapshot audit and V422 consecutive Entries parser.
- `shyt_yt_world_delta_fence_v423.h` arms **only after** matching
  V419 Welcome + explicitly requested authenticated V421 Snapshot.
  It records epoch, snapshot cursor, server last, old replays,
  consecutive advances and heartbeats; epoch jump or a missing
  sequence revokes the trusted observation context.
- Original encrypted UDP loopback regression proves replay after snapshot
  is ignored and a subsequent contiguous batch advances the *read-only*
  cursor. All world payloads remain in bounded quarantine. This is NOT
  in-game world synchronization, gameplay authorization, release,
  direct P2P or a server-side CPU/bandwidth optimization.
- V423 pilot Linux/Windows CI: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/42246644464
  (SUCCESS on both jobs, 2026-11-06).

## Next release-blocking validation

1. Implement a complete **typed, bounded Snapshot/Entries application
   consumer**, with original server epoch/sequence semantics and a
   rollback/reconnect plan. Verify against original v1.4.0 generated
   protobuf; bind only after validated BBHost 1.09 in-game NetSync
   send/receive and remote actor hooks.
2. Separate **authoritative reliable world/events** from **permitted
   authenticated direct unreliable movement**. Before sending direct,
   require server-issued party lease, peer identity, NAT probes,
   per-channel limits, expiry, dual-route duplicate suppression and
   deterministic relay fallback, with rate/traffic caps.
3. Five real clients/PCs, all YT 1.4.0 edition, mixed maps and roles,
   hot joins, Dream, boss/DBNO, travel/death/host exit, saves and reward
   parity; simulate latency, loss, jitter, reorder and 5-15s outages.
4. Compare measured Fornex ingress/egress and CPU, GPU FPS/1% lows,
   memory/VRAM and packet loss against the original release with matched
   conditions, then wrap in one signed/rollback-ready launcher.
5. Never promote or deploy until those gates actually pass.
