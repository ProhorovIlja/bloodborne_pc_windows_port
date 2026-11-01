# Playable track: Yharnam Together while true Windows-native AOT develops

**Separate experimental branch from the independent native-port PR #84.** Nothing
here was linked into the current Yharnam Together client or server, deployed
to Fornex, or presented as a shipped mod feature.

## Playable today, independently of the future true native source-port

Public **released and actually playable** Yharnam Together v1.3.1 (published 2026-10-31, exact official commit `5d2305ee611ef1e03be39ff925f0da75c9a70393`):
- Exact release: https://github.com/lKaniel/bloodborne-server/releases/tag/v1.3.1
- Setup and portable ZIP are both published and signed with SHA-256 checksums in the release notes.
- New in v1.3.1: friends, open teams/join modes, host handoff, optional boss tempo, launcher portability/diagnostics, boss AI and performance fixes. **These are in the release already, do not reimplement them.**
- Releases: https://github.com/lKaniel/bloodborne-server/releases
- Install guide: https://bloodborne.seamlesscoop.dev/docs/install
- Game team guide: https://bloodborne.seamlesscoop.dev/docs/play
- Official server protocol/source used to compile the experiments:
  https://github.com/lKaniel/bloodborne-server/tree/5d2305ee611ef1e03be39ff925f0da75c9a70393/server/coop

**Exact published constraints:** current upstream team lobby still
`TeamSize = 4`, and upstream invasions have
`InvasionMaxPlayers = 4`. Its server routes game's native network packets
through the server; it does not implement direct P2P yet. Even if some
existing port documentation calls its Windows game a native port, the
user's separate goal remains a FULL Windows game without original
PS4 EBOOT/code loaded at runtime. The published current compatibility
implementation does NOT meet that stronger requirement.

Do not tell players that five hunters or hybrid P2P work in v1.3.1.
A room cannot exceed the game's actual remote entity slots simply by
changing a server const. The hosted service must not replace or be
upgraded over the Fornex production BBSC server without a dry run and
explicit permission.

## v1.3.1 integration priorities from the full GitHub/forks/PR sweep (2026-11-01)

The latest main branch is the same commit as v1.3.1, but numerous **open PR heads** contain post-release candidate code. These are NOT shipped and must be tested as separate changes against the pinned release. Details and cross-repository priorities: [UPSTREAM_WATCH_20261101.md](UPSTREAM_WATCH_20261101.md).

## Safe v1.3.1 launcher download check (source-only utility)

`verify_yt_v131_release.py` is a standalone, **read-only offline**
check for the official v1.3.1 Windows setup EXE / portable ZIP. Its
allowlist includes the exact names, byte sizes and SHA-256 hashes
published by the official 2026-10-31 release (no binary mirrored).
Use `python3 playable-track/verify_yt_v131_release.py PATH_TO_DOWNLOADED_FILE`
before running an installer if you want an extra manual integrity check.
It rejects truncated, modified or wrong-version assets, unknown names
and symlinks. CI tests the verification logic with invented fixture
bytes and checks that the embedded official hashes match the release.
It is **not yet embedded into YT's own updater** and cannot guarantee
that an upstream maintainer's account or HTTPS distribution is secure.

## Upstream 1.3.2 five-player candidate: do not duplicate it

As of 2026-11-01, the released YT version is **1.3.1**, but maintainer
Draft PR https://github.com/lKaniel/bloodborne-server/pull/484
already introduces five seats in server, emulator, HUD, portraits and
game/client structs. New Draft #486 adds a real five-game rig scenario,
while #485 covers Global quick match. These are NOT yet a published
integrated release or proof of five successful gaming PCs.

Our read-only source and actual original C++ HUD/portrait checks against
the exact #484 commit run on Linux and Windows in
.github/workflows/yt132-pr484-five-seats-source.yml. The fixture validates
four other hunters' visible portrait slots and five across team UI
alongside source contracts; it does not launch five games. Keep our
earlier independent V194/V195 patches as historical/research references,
NOT blindly stacked over this upstream branch. This is separate from
our still-unfinished authenticated hybrid Direct P2P integration.

See UPSTREAM_WATCH_20261101.md for the #477-486 PR prioritization.

## Actual real-source v1.3.1 hybrid transport work

`hybrid_direct_ingress_v2.h` validates an already authenticated
direct-peer `GameFrame` before passing it to the original
`GameLinkPeer` that both relay and direct paths MUST share. Checks
source identity/instance, current local session, exact native
movement envelope, and refuses to carry reliable-world ACKs inside
direct movement-only packets. A real C++20 test compiles the
**published v1.3.1** `coop/game_link.h`, delivers movement first
direct then through relay, deliberately injects duplicate, replay,
out-of-order and spoofed packets, checks server fallback and verifies
reliable messages still arrive exactly once on the original stream.
This is still a POLICY+INGRESS PROTOTYPE, not working direct UDP
transport or P2P player support in shipping YT.

**Pair-bound lease safety (2026-11-01):** A server-granted DirectPeer
route must now identify a nonempty ordered sender/receiver pair.
Ingress checks that the authenticated sender and local account match
**that exact lease**, rejecting a grant borrowed from another hunter
or another receiver after handoff/rejoin. Added C++20 negative tests
for mismatched sender, receiver, and missing account identity. This
prevents policy-level cross-peer lease reuse but does NOT implement
cryptographic UDP authentication, server lease issuance or NAT traversal.

## V1 safe hybrid direct/relay transport EXPERIMENT

`hybrid_transport_policy_v1.h` uses the **exact actual upstream's
`coop/packet_routes.h`**, inheriting its native channel policy.
`ChooseNativePacketCarrier`:

1. Applies upstream `RoutesNativePacket` first. Its SameMap, Ours,
   Drop, owner/follower and native channel rules are NEVER skipped.
2. Defaults every eligible packet to `Server` (or the original
   `Drop`). Reliable channel 7+ stays server, as do all world log,
   membership, inventories, RPC, invitations and invasion channels.
3. Only `0x06` unreliable player movement in **the same known map**
   is a direct candidate. Direct requires both users opting in,
   matched protocol, authenticated current party session and peer,
   successful authenticated UDP path verification, and a
   server-authoritative per-map route lease.
4. The route grant must belong to the current game/world epoch,
   neither endpoint is an invader, and the signed-in peer's direct
   heartbeat is fresh within 2500 ms. NAT failure, lost path,
   map change, epoch mismatch, grant expiry or feature mismatch
   immediately reverts to server.
5. All other channels and unrecognised channels use exactly the
   ordinary server transport and existing filtering rules.

The C++20 tests use the real public YT upstream `GameLinkPeer`
and `RoutesNativePacket` definitions, testing positive and
negative cases for all individual safety gates, dropped world
channels, other native data channels, expiry, hostile peers, and
map transitions. The GitHub Actions job pins the *actual upstream*
commit and also verifies that the published original four-player
limits are still in place.

**NOT implemented or validated:** authenticated peer key exchange,
NAT traversal, integration into game's actual send/receive path,
server lease issuing, switch-over sequence continuity,
dedup across server/direct carriers, real five-player client entity
slots, game visuals, PvP, and traffic/performance improvements.
Enabling direct from this header alone would not work and is not
recommended. Any direct mode must remain off by default until end-to-end
client/server and 2/3/4/5-player tests prove it.

### Minimum test matrix before turning P2P on

- Two to four hunters (upstream supported) on one map, two maps,
  Hunter's Dream, boss fog and chalices.
- Network jitter, packet reordering, UDP loss, symmetric NAT,
  Radmin/VPN and no VPN; peer path dies mid-boss.
- Host changes maps, leaves, loses internet, invader joins,
  world epoch resets, respawn/DBNO, team wipe, reload.
- Reliable game packets remain ordered exactly once, with native
  channel drop rules, without stale/replayed packets after P2P
  to relay failover.
- CPU/bandwidth per session compared against current relay-only
  with the **same scenario** and counters. No 200-player
  scalability claim without a reproduced load test.
- Five total-player configurations must be separately implemented
  and proved in both game and server, including combinations of
  cooperators and invaders. A server max setting alone is not enough.

## Delivery order

**Now:** play with existing tested v1.3.1, preserving original saves
and avoiding live experimental server upgrades.
**Next:** implement negotiated, cryptographically authenticated peer
path with relay default, full packet sequence/dedup and failover tests.
**Then:** validate native client remote slots and extend team+invasion
capacity to five with authoritative regression tests.
**Parallel native game:** PR #84 continues original full
Bloodborne 1.09 AOT/gameplay/Windows engine; no guest-runtime
dependency may be silently relabeled native.

This branch belongs to its own Draft PR; do not merge without
playtest and server/client compatibility checks.


## V232–V233: launcher and server improvement work, not duplicated UI

- `yt_launcher_mod_conflicts_v232.py`: read-only preflight against the
  actual YT v1.3.1 `bbport/scripts/mods.py`, respecting existing
  `mods.json` order, adjacent `CUSA03173-mods` overlay and the
  original file-layout logic. Flags competing whole-file mod overrides,
  especially gameplay-critical param/event/map/script modifications,
  and optionally computes a bounded SHA-256 of final gameplay winners.
  Existing Mods UI is retained; this module is a **candidate JSON
  provider for it**, not yet wired to production. Source documentation:
  [V232](V232_YT_LAUNCHER_MOD_COMPAT_AND_UPSTREAM_PLAN.md).
- `yt_server_capacity_gate_v233.py`: accepts two compact JSON
  summaries from the *existing* YT `server/loadtest/run_load.py`,
  rejects incompatible simulated player populations, and checks
  explicit CPU, p99 relay latency, outbound bandwidth, refused
  sessions and buffer-drop budgets. It DOES NOT start a real
  server or claim any observed live performance gain.
  Source documentation: [V233](V233_YT_SERVER_LOAD_CAPACITY_ACCEPTANCE.md).
- Source-backed parallel candidates include
  `visy/bloodborne_pc_windows_port` documented direct UDP, reliable
  host control, NAT, network simulation, session identity and save
  protection, plus BBHost renderer/online logic. **None is
  demonstrated interoperable with YT**, and GPLv3 reuse must
  respect license constraints. No CLS nonpublic material published.

CI with exactly the released YT v1.3.1 scripts and invented game data:
V232 https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41333733614
(Windows/Ubuntu PASS);
V233 https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41334107718
(Windows/Ubuntu PASS).

Before shipping, finish actual launcher integration, exact game/patch/
mod/hook handshake, authenticated P2P UDP & safe fallback, real five
player world/entity tests, staging load benchmarks, backup/rollback,
and a production runbook. Fornex remains unchanged.
