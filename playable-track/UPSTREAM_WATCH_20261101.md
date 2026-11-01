# Upstream research ledger: 2026-11-01 (v1.3.1 baseline)

## New 2026-11-01: YT 1.3.2 DRAFT candidates, NOT v1.3.1 release

Source/metadata checked at distinct PR heads. Do not merge, deploy or describe
these as one tested integrated release. Official last release is v1.3.1.

- **#484 Teams of five** https://github.com/lKaniel/bloodborne-server/pull/484
  pinned f19696f32833161aa2300b36321d8c5c4d663c6b. Real code includes
  TeamSize=5; signs 7,6,5,4; InvasionMaxPlayers=5; four game HUD entries;
  emulator PartyListSize=4 and PortraitSlotCount=4; port SlotCount=4;
  five client lobby member slots. Reuse this upstream work instead of
  blindly stacking our historical V194/V195 source modifications over it.
  Server source unit tests are NOT evidence of a real five-client session.
  Our PR #85 checks this exact upstream cross-layer C++ source candidate
  and compiles the original game HUD/portrait layout on Linux/Windows.
- **#486 Five-game rig** https://github.com/lKaniel/bloodborne-server/pull/486
  pinned 3e677729e3691c4f068eeb76e52a9f37b1eeb213. Adds guest4,
  five-hunters lamp trip, code/open join, hosted fake-Discord scenarios.
  Draft source existence is not a confirmed passed live-game session.
- **#485 Quick match** https://github.com/lKaniel/bloodborne-server/pull/485
  pinned 53d23c886e3ef8ab3b6fd702c749ae060bcca979. QUICK_MATCH=29
  avoids RESET_LAMPS=28; level-aware open team or creates one, Global-only.
- **#479 Team duels** https://github.com/lKaniel/bloodborne-server/pull/479
  teams/FFA and last team standing; NOT proof of 3 simultaneous invaders.
- **#481 Global/Discord auth** https://github.com/lKaniel/bloodborne-server/pull/481
  browser OAuth PKCE/HTTPS for Hosted Global; needs external Discord app
  credentials/config, not an automatic upgrade for a Local Fornex server.
  Cross-shard logout limitations remain explicitly noted by author.
- **#482 Optional Discord Rich Presence**
  https://github.com/lKaniel/bloodborne-server/pull/482 ; off by
  default, public-server join only, requires Discord application id.
- **#483 Team-visible lobby** https://github.com/lKaniel/bloodborne-server/pull/483
  shows hunter's group in online/friend lists.
- **#480 Shard load caps** https://github.com/lKaniel/bloodborne-server/pull/480
  reports 300/300 synthetic playing, relay p99 9.8 ms and 0.14% loss
  for 60 s on their tested host. Not measured Fornex QoS or full game.
- **#477 Backend reply cap** https://github.com/lKaniel/bloodborne-server/pull/477
  bounds bloodstain, ghost and message responses after observed oversized
  answer crash; high-value client stability when officially integrated.
- **#478 Launcher repairs** https://github.com/lKaniel/bloodborne-server/pull/478
  frozen SSL-context fallback, Windows CLANG64 DLL packaging and UTF-8 env.

**Integration decision:** retain v1.3.1 playable baseline until upstream
1.3.2 PRs are reconciled and actually tested. Prefer upstream five-player
implementation to duplicating our prior isolated server-only patches.
Require genuine 5-process join/leave/lamp/boss/wipe/reconnect and 4+1,
3+2, 2+3 hostile slot tests before claiming any combinations. Develop
authenticated direct P2P+NAT traversal, unified GameLinkPeer sequence
and fallback in separate gated code. None of these PRs delivers that.


**Scope:** check live release commits and open, unmerged PR heads across
Yharnam Together, its close relatives and forks, standalone P2P
implementations, other PC runtimes, rendering, server performance and
launcher packaging. Source provenance in the links below. This is a
**triage report**, NOT a claim that every GitHub repository was cloned
or that unmerged changes were already compiled into our executable.

## Correct released baseline: Yharnam Together v1.3.1

- Latest release checked: https://github.com/lKaniel/bloodborne-server/releases/tag/v1.3.1
- Published 2026-10-31 at 13:56 UTC; release's true source commit:
  `5d2305ee611ef1e03be39ff925f0da75c9a70393`.
- **v1.3.1 already ships**: friends, open/invite/join modes, host
  handoff, optional boss tempo, per-world lamp resets, setup UI,
  portable ZIP, more reliable Windows launcher logs/certificates,
  boss owner/AI, guest frame stutter and other extensive fixes.
  DO NOT port duplicate old PR #423 as if new: it was included
  in the published v1.3.1 release.
- Shipping limit: server team lobby `TeamSize=4` and invasion
  `InvasionMaxPlayers=4`; the game only supports the matching
  number of client-visible entity slots. Native game packets use
  YT's server relay by design, not negotiated direct P2P.
- The release calls its game runtime "native port", but
  https://bloodborne.seamlesscoop.dev/docs/architecture says
  it still **loads original PS4 game x86-64 code** through a
  small compatibility runtime. This does not satisfy the separate
  **no-original-EBOOT-at-PC-runtime** source-port goal in PR #84.
- Latest main HEAD matched v1.3.1 at audit time. Open PRs below
  are NOT published 1.3.1 code.

## Priority A: current Yharnam Together correctness and real playtests

1. **PR #475**, https://github.com/lKaniel/bloodborne-server/pull/475,
   "team guest no longer leaves when invader arrives", a confirmed
   v1.3.1 regression. Session member count subtracted the invader
   ~5 seconds before the invader physically joined the room, making
   the guest erroneously abandon the host. The candidate only
   subtracts once the invader's name appears in game session members.
   Author's tests green; rig 2/4 invasion runs passed, 2/4
   stalled in invader's first load. **TRACK / regression test
   before promoting**, do not pretend fully fixed.
2. **PR #471**, https://github.com/lKaniel/bloodborne-server/pull/471,
   guest Doll level-up state events. Conflict/partial rig.
   **VALIDATE** on normal and solo guest story scenarios.
3. **PR #470**, https://github.com/lKaniel/bloodborne-server/pull/470,
   Yahar'gul mummy interaction after One Reborn. Measured
   event-button hit sector mismatch. **VALIDATE** reachability
   with host and guest, don't alter generic input globally.
4. **PR #451**, https://github.com/lKaniel/bloodborne-server/pull/451,
   Ludwig boss exit wall in Hunter's Nightmare.
   **VALIDATE** map-event persistence across reload and boss clear.
5. **PR #467**, https://github.com/lKaniel/bloodborne-server/pull/467,
   client-local hide phantom glow; OFF by default. Good optional
   presentation work **after** stability, avoid changing host state.

## Priority A: proven FIVE-player and peer-to-peer reference

- **Nightwatch Co-op**, https://github.com/vladtepes22/NightwatchCoop,
  updated 2026-10-31. Public release **0.2.6-beta.3**:
  https://github.com/vladtepes22/NightwatchCoop/releases/tag/v0.2.6-beta.3 .
- Its README documents **up to 5 simultaneous hunters**,
  game-to-game peer communication, joinable co-op without separate
  relay-only authoritative world server; direct VPN/Tailscale-like
  connectivity via its optional Nightwatch Online OpenVPN tunnel,
  and public tests `engine/tests/test_party_net.cpp`,
  `test_party_nat.cpp`, `test_party_fourp.cpp`,
  `test_party_host.cpp`, `test_party_pvp.cpp` and QA matrix.
  The README's five-player claim is a **different engine/mod's
  published feature**, NOT evidence that YT 1.3.1 runs five.
- Nightwatch's QA explicitly says its five-process `fiverejoin`
  scenario is manual and needs ~40 GB commit. Its own
  INTEGRATION report says extended campaigns and real Internet/NAT
  traversal are not fully covered by its current testing.
- **Design donor:** inspect its client entity-slot mapping, peer
  transport/connection resume and NAT failure handling, plus test
  matrix. Do NOT mechanically copy Nightwatch's global networking
  code into YT's server-authoritative world: the world-ownership,
  streaming and save semantics differ.
- **Related direct P2P research:** https://github.com/Wozzardman/shadnet-p2p
  uses P2P with a private shadNet signaling server and Tailscale,
  but its README warns that traditional signaling game protocol
  TCP 31313 is **unencrypted**. Do not deploy it publicly as a
  drop-in YT server or claim it supports YT's world sync.
- Original **CLSAMG22/BBSC**:
  https://github.com/CLSAMG22/BBSC , newer client stacks forked
  by community mods, not the current YT 1.3.1 protocol.
  RadminBell: https://github.com/joaoedualves/RadminBell,
  a private BBSC 0.0.2 server UI, not a YT backend.

## Priority A/B: server scalability, sequencing and durability

- YT **#444** https://github.com/lKaniel/bloodborne-server/pull/444
  adds `bbload --owners N` to simulate multiple map enemy owners
  rather than just a leader. Important for our modest
  Fornex server; before making claims about 200+ player support,
  measure worst-case CPU/UDP bandwidth with 4 (later 5)
  owners and same-map vs separate-map load.
- YT **#438** https://github.com/lKaniel/bloodborne-server/pull/438
  makes durable per-account invasion reward grants and ACKs,
  dependent on #436 and #437. Never enable unfinished
  capability alone. Require disk atomicity, duplicate grants
  after a crash and old client interop checks.
- YT **#450** https://github.com/lKaniel/bloodborne-server/pull/450
  cross-platform Linux server/client. The branch author reports
  Linux-Windows test success, but PR remains unmerged; good
  test donor for Ubuntu Fornex and docker build reproducibility.
- The YT server's `coop/game_link.h` keeps the authoritative
  reliable sequence, resends, ordering and latest unreliable
  packet per channel. Hybrid direct P2P MUST use **the same
  per-peer stream state** across carriers; otherwise stale data
  and replay can corrupt sessions or cause guest disconnects.
  Our V2 native test `test_hybrid_direct_ingress_v2.cpp` uses
  **this exact published original C++ GameLinkPeer** to verify
  a duplicate after direct/server fallback is discarded.
- Do NOT deploy the standalone policy header into production:
  it does not implement authentication, NAT or direct UDP.

## Priority B: launcher/client performance and stability

- **Supermedo Windows port**, https://github.com/Supermedo/bloodborne_pc/pulls:
  #140 frozen launcher and nested runtime packaging checks (priority high
  for preventing broken updates); #145 first-run automatic settings;
  #141 RX 6000 driver descriptor safety; #144 bounded GPU motion
  cache; #147 1.09 GOTY dump detection. These are open
  candidates, not official YT v1.3.1 bug fixes.
- **Deadinside bbport**, https://github.com/deadinside28/bloodborne_pc/pulls:
  #414 ensure Linux online setting does not skip actual network
  selection; #415 select in-game menu language correctly on
  Windows; #417 post-respawn collision proxy reset (**author
  says hypothesis and only intermittent observations**);
  #418 clear guest spectator state after boss wipe and host
  reload (**needs rig re-test**); #400 reproducible gameplay
  route recording for performance regression tests.
- **BBHost**, https://github.com/droogie/bbhost/pulls:
  #117 unbounded optional disabled-trace dispatch record
  accumulation (~14 MiB/min according to PR report; exact
  host-specific evidence), high-value long-session perf donor;
  #196 GPU command-processor threaded commit optimizations,
  requires GPU/replay parity tests; #188 configurable gamepad
  remap/hold/swap; #161 Discord Rich Presence for
  character/level/location with IPC reconnect. Do not
  add its game-runtime subsystems wholesale to YT.
- **Community launcher**, https://github.com/wanderabyss/sunbros-bloodborne-launcher
  has Qt Quick installer/UI, mod workshop and newer
  upscaler options but is built on BBSC 0.0.2; use as
  UX / updater / packaging design reference, NOT as an
  interchangeable YT client binary.
- **Independent YT online-service mod**,
  https://github.com/SebValentine/Yharnam-Together-HuntersDream-Services-mod
  claims optional split of game messages/chalice content
  from YT team server. It is a third-party launcher mod
  with no verified integration in our setup. Test privacy,
  HTTPS, service failure and login separation before
  considering it.

## Priority C: other runtime and graphics donors

- shadPS4 upstream PRs #5597 shader MSAA arrays,
  #5549 thread-ID buffer addressing, #5596 audio pacing,
  #5594 atomic rename/flock, #5534 fcntl, #5425 CRT
  guard functions. Only borrow verified semantics,
  not emulation-only runtime architecture.
- bloodborne-native/bloodborne-recomp at original pin
  8f31ec7 (2026-10-30), separate true-native Windows
  research branch is Draft PR #84.
- Other checked repositories/forks include
  `Huarch/Bloodborne-Lantern-BBSC`,
  `Rijaak/BBSC---Linux-and-Steamdeck`,
  `visy/bloodborne_pc_windows_port`,
  `Mrsuss60/bloodborne_pc_windows_port`,
  `NightwatchCoop` forks and
  `shadnet-p2p` forks. Their features require independent
  source/licensing and reproducible build verification.

## Deliverable and truthfulness

- Official public version = **YT 1.3.1**, not 1.3.0.
- Our own playable PR #85 = **source-only guarded P2P policy
  and real-upstream frame/sequence regression tests**,
  **not an updated playable YT runtime**.
- Our independent original-game native PR #84 remains separate.
- Never send user game EBOOT/ELF, extracted game assets
  or recompiled game functions to public GitHub/CI.
- No live Fornex, published launcher, server or
  user saves changed; Draft PRs are not merged.
