# Upstream research ledger: 2026-11-01 (v1.3.1 baseline)

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
