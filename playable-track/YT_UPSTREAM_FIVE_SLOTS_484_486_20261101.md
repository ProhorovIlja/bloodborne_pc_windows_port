# Yharnam Together source audit: upstream teams-of-five PRs #484/#486

2026-11-01. This notes ONLY publicly retrievable GitHub changes,
NOT private Discord conversations or unreleased collaborators' code.

## Verified public upstream

- Official `lKaniel/bloodborne-server` latest tagged release remains
  **v1.3.1**, published 2026-10-31.
- `lKaniel/bloodborne-server#484` (`Teams of five`) is
  **OPEN/DRAFT**, pinned observed head `f19696f32833`.
  It touches 28 files. Explicit source-code changes include:
  - `server/coop/team_lobby.h`: `TeamSize = 4` to `5`.
  - `emulator/src/core/bloodborne_host_rules.h`:
    `TeamSlots = 4` to `5`.
  - `server/coop/invasions.h`:
    `InvasionMaxPlayers = 4` to `5`.
  - `emulator/src/core/bloodborne_party.h`:
    `PartyListSize = 4` (previously 3), reflecting a host
    plus four remote participants.
  - Includes HUD, portrait, server, rules, invasion and launcher
    changes. Changing *only* a server `TeamSize` constant is not
    sufficient to provide five in-game player slots.
- `lKaniel/bloodborne-server#486` (fifth game rig, join-code/open
  teams, global server/fake Discord) is **OPEN/DRAFT**, observed head
  `3e677729e369`. It changes nine rig/world-test files,
  including `tools/rig/scenarios.py`, where team-separated world
  flags and stale NPC hostility checks are introduced.

## Product-level implications for YT PR #85

Do not duplicate these upstream changes blindly. Required before merging
our hybrid P2P or claiming five-player availability:
1. Rebase/integrate the exact tested five-slot upstream sources
   across server + client + HUD + invasion rules, **not server only**.
2. In a real five-client session, verify all members have unique
   server-authorized *session-instance* identities, not merely
   different display names or local UDP ports.
3. Test 5 cooperators, 4 cooperators + 1 invader, 3 + 2, and
   2 + 3 ONLY when explicitly permitted by final tested host policy;
   never assume every mix is implemented by the upstream draft.
   Validate full sessions do not admit an extra invader.
4. Test leader already loaded in game (hotjoin), Hunter's Dream
   remote-actor visibility, map transitions, correct names/roles,
   DBNO and offline/failed member HUD state.
5. Confirm distinct teams' flags and story event data do not leak,
   including the PR #486 cross-team NPC-hostility rig scenario.
6. Validate our `PeerRouteLease` ordered sender/receiver binding and
   direct UDP channels against these 5-slot session members.
7. Test NAT/rebinding, 2 clients on one PC with distinct local UDP
   ports, and remote network conditions; retain safe relay fallback
   for necessary traffic, without forcing all gameplay through
   limited-capacity Fornex VPS.
8. Measure actual five-client host CPU, network bandwidth and
   relay cost before public release.

These are test/merge gates, not successful in-game measurements.
PR #85 remains a source-only experimental transport policy;
no automatic merging, no Fornex changes or public client release.
