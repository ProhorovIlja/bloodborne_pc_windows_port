# 2026-11-01: BBHost, Lantern Engine and Yharnam Together coexistence

**Primary user target remains Yharnam Together** (client/launcher/server)
with up to five players, authenticated Direct P2P for eligible gameplay
traffic and a lightweight central server for matchmaking/state/authority.
A true no-EBOOT, standalone PC port remains separate PR #84.

## What public source actually establishes

BBHost source: https://github.com/droogie/bbhost
- `docs/online.md`: server-mediated NP Matching2 matchmaking, private
  server account/room events, direct peer UDP with NAT traversal (STUN,
  hole punching) and relay fallback. A second instance on one PC
  takes the next available P2P port rather than binding the same port.
- `src/net/stun.h` documents a BBHost-specific relay-HELLO/reply token
  protocol. Its tokens and framing **are not the YT authenticated
  wire protocol**; do not copy packets or bypass YT session membership.
- `docs/online.md` says BBHost sessions are BBHost-only. A report that
  somebody is *trying* BBHost/BBPort crossplay is a research lead,
  **not a delivered interoperable feature**.
- The documented five-player BBHost feature means selected areas can
  take two invaders, not YT's independent 5-person co-op target.
- `docs/performance.md` supplies stage-level CPU/GPU bottleneck
  readings. Reuse the measurement methodology, not unverified claims
  that one release objectively outperforms another.

Lantern Engine source: https://github.com/Awakenchan/LanternEngine
- It starts from BBPort/shadPS4-derived technology with additional
  renderer, memory, shader, GUI and launcher work.
- The current project requires the owner to provide their PS4 game
  executable. It's an alternative PC execution solution but **not**
  itself proof of a standalone no-EBOOT Bloodborne PC port.
- GPLv3 source and the project's NOTICE/credits/trademark restrictions
  must be reviewed before reuse; do not paste code into YT blindly.

## Specific experimental issues reported by players

1. Some merged test builds reportedly cannot hot-join a leader
   already loaded in the game. Clean official YT 1.3.1 was not
   demonstrated to have this issue. Need exact test commit SHA, log
   state machine IDs and 2-PC comparison.
2. Player name/HP can appear with invisible remote game actor after
   Hunter's Dream joins or map transitions. Test actor-creation
   acknowledgment and per-target member identities; UI presence
   does not prove remote world entity exists.
3. `?ActionEventInfo?` guest role display already has
   `NameUnnamedGuestRole` in original upstream YT 1.3.1; check
   merged-build regressions rather than duplicate it.
4. Multiple copies on one PC must have **different UDP endpoint/port,
   unique session-instance identity, and unambiguous server-issued
   ordered sender/receiver leases**. Distinct ports alone do NOT
   make two cloned online accounts unique; reject ambiguous identities.

## Implementation acceptance gates for YT Direct P2P

- Server authorizes the exact sender, receiver, world epoch, map, team
  and instance on an authenticated channel.
- Explicit NAT/STUN candidate collection per local UDP socket,
  authenticated peer handshake, endpoint change revalidation,
  anti-replay sequence numbers and a shared per-channel deduplication
  domain even when relay and direct UDP packets interleave.
- Reliable/auth/room events remain server-authoritative. First eligible
  direct channel is native unreliable movement, channel 0x06 as
  documented by our experimental source-only policy.
- If direct route fails, safe server fallback only for allowed
  traffic; never silently assume the Fornex VPS can relay all
  player-to-player movement for 200-600 users. Load-test server CPU,
  bandwidth and session-count with observed metrics.
- Run actual same-PC multi-instance, distinct PCs, map travel,
  Hunter's Dream, 5-client group, invasion/duel, packet loss and
  relay-fallback tests before release.
- Never promise compatibility between YT and BBHost/BBPort: different
  matchmaking/transport/guest state protocols until proven with
  real protocol captures and a supported bridge.

## Current boundaries

Our YT PR #85 is Draft; policies and ingress tests remain
**source-only**, not production P2P. Upstream YT 1.3.2-related PRs
#484 and #486 were still Draft when checked. Do not redeploy Fornex.
No private Discord screenshots, unreleased source, or interpersonal
claims are to be published from this research.
