# Seamless Hunt: Bloodborne PC

**An independent, experimental downstream of [Yharnam Together](https://github.com/lKaniel/bloodborne-server), not a replacement with the Visy launcher or the older Windows-port launcher.** The native Windows game, Yharnam Together BLauncher, co-op runtime, Qt shadNet backend, and Ubuntu 24.04 Fornex staging server all share a single pinned upstream source baseline.

> **Not a public player release.** Game startup, real co-op, NPC signs, guest doors, cross-client PS4/CLS interoperability and the full launcher/server kit still require end-to-end tests. Nothing here changes the production Fornex server or the `master` branch. The project contains no retail Bloodborne game files.

## Credits, copyright and upstream licenses

**Built on the work of others, with attribution.** Seamless Hunt incorporates a
pinned, modified Yharnam Together source build, which already credits the
original native-port developers, shadPS4, co-op and shadNet contributors, and
third-party graphics, shader and middleware authors. We maintain the original
authors' copyright, licenses and notices. **We do not claim their work as
ours or imply their endorsement.**

**[Full author credits and provenance](CREDITS.md)** ·
**[Third-party license notices and release obligations](THIRD_PARTY_NOTICES.md)** ·
**[Rules for importing code from external forks](CONTRIBUTING.md)** ·
[Official upstream Yharnam Together credits](https://github.com/lKaniel/bloodborne-server#credits-and-forks).

> Public source on GitHub is **not automatically open-source licensed**.
> The pinned Yharnam Together project states **GPL-2.0-or-later**; the
> historical root `LICENSE` in this repository contains **GPLv3**.
> Each component retains its own terms. This project must complete
> the compatible-license, copyright-notice and corresponding-source
> audit **before distributing its combined binaries**. No game's
> proprietary files or private data may be bundled.

Our project is unofficial and is **not affiliated with, sponsored by or
endorsed by** Sony Interactive Entertainment, FromSoftware, the Yharnam
Together maintainers or any third-party developer listed in the credits.
`Seamless Hunt` is not a statement of collaboration by those authors.

## The single source of truth

| Component | Primary source used in the actual candidate | Our changes |
| --- | --- | --- |
| Native game + renderer | [Yharnam Together](https://github.com/lKaniel/bloodborne-server) `bbport/` | Shader/texture resource guards, long-session diagnostics, in-game HUD/quit and staged spectator tools |
| Windows launcher | Yharnam Together `bbport/launcher/bbport_launcher_win.py` + `bbport_coop.py` | Seamless Hunt-specific release channel, game event packaging, safe game/patch handling |
| Co-op + game network | Yharnam Together `bbport/gpu/bbcoop/`, `emulator/src/core/` and `server/coop/` | DBNO, server admission/rate limits, auth revocation, conservative transport safeguards |
| Windows co-op host | Yharnam Together `server/` | MSVC Qt 6.8.3 server build, separate verified native runtime staging |
| Dedicated Fornex host | Same Yharnam Together `server/` | Ubuntu **24.04**, exact **Qt 6.8.3** build and backend/account test gates |
| Future website | Our own source-only Hunter Portal prototype | Privacy-safe, verified telemetry planned; not live |

**Pinned and currently built**: [lKaniel/bloodborne-server@77e3507](https://github.com/lKaniel/bloodborne-server/commit/77e350743a7cb4524cfcc1782fb6e3af64e25b15), corresponding to Yharnam Together **v1.1.9**. The newer **v1.2.0** (`08e56cd...`) is a candidate for controlled porting; it is **not silently in this build**. All components must advance together after conflict, ABI and protocol review.

Canonical development branch: `feature/seamless-hunt-mainline`. [Source-of-truth lock](tools/poc/yharnam/mainline/source_of_truth.json) is checked by [CI](.github/workflows/shyt-mainline-source.yml). Historical `feature/yharnam-v*` branches are previous experiments, not other products.

## What is intentionally NOT our mainline

The older `master` branch is based on earlier deadinside28/Mrsuss60 native Windows code with a **different launcher**, and remains for reference. The experimental mainline instead fetches the pinned Yharnam Together sources in CI and applies source-checked overlays via [compose_sources.py](tools/poc/yharnam/unified-v9/compose_sources.py). This is not a switch to Visy's launcher, and it is not a standalone shadPS4 emulator build.

Yharnam Together already incorporates upstream work from deadinside28, Supermedo, parts of the shadPS4 rendering stack and others. Further BBHost, Visy, deadinside, FireBurn, Supermedo, shadPS4 and CLS fixes are **review candidates**, not blind bulk merges. Every import needs original authorship/license attribution, a pinned commit, gameplay/online version compatibility, before/after performance measurements and a rollback.

## Community interoperability and responsible comparisons

Seamless Hunt is a **temporary, optional proof of concept** and is not intended
to force anyone away from CLS BBSC, Nightwatch, Visy, Yharnam Together
upstream, The Hunter's Dream or other communities. We credit original
authors and assess co-op fixes on their technical merits, without
unsupported claims that another team copied code, that one project is
unplayable, or that different networking protocols already cross-play.

**Different servers and co-op implementations are not interchangeable just
because they have the same game UI.** We will only advertise cross-client
support after compatible two-PC tests, not combine incompatible public
player counts or migrate logins, saves and passwords automatically. If a
better-maintained option becomes available, a voluntary, staged and
reversible migration is preferable to permanent lock-in.

[Independent co-op approaches, evidence rules and migration plan](docs/COOP_INTEROPERABILITY_AND_MIGRATION.md).

## Transport and gameplay feature priorities

**The current Yharnam Together team mode is server-relayed UDP, not a
fully direct player-to-player connection.** The upstream
[`SERVER_COOP_PLAN.md`](https://github.com/lKaniel/bloodborne-server/blob/77e350743a7cb4524cfcc1782fb6e3af64e25b15/docs/SERVER_COOP_PLAN.md)
documents one UDP link per hunter to shadNet, server-forwarded game packets
and an authoritative shared world. Older direct-P2P notes refer to a
superseded development stage.

A future **opt-in hybrid P2P / relay fallback** must preserve world
authority, reconnects, privacy, NAT traversal and protocol compatibility.
It is not yet implemented or benchmarked. Our machine-readable
[transport and feature review](tools/poc/yharnam/mainline/transport_and_feature_priorities.json)
has hard-fail tests preventing unsupported P2P or low-server-load claims.
The [game traffic capacity tool](tools/diagnostics/game_traffic_capacity.py)
can model relay fanout from **assumed** bandwidth, but cannot claim real
Fornex CPU, RTT or game traffic until actual instrumentation is recorded.

We review design concepts from **LukeYui's Elden Ring Seamless Co-op**,
**Demon's Souls**, **Dark Souls**, **Sekiro** and **Elden Ring**, as well as
other Bloodborne forks. These are **ideas for future, license-reviewed
implementation, not claims that we imported their source code**.
Priority is strictly: (P0) boot/launcher/joins/consensual opt-in invasions/saves/NPCs/doors/stable long
sessions and network measurements, (P1) experimental hybrid P2P and reliable
transport recovery, (P2) optional training, camera, filters and accessibility.
PvE-only parties must never be involuntarily exposed to invasions.
Experimental gameplay additions remain opt-in until validated.

## Remote Fornex staging endpoint support (V46)

The **original Yharnam Together BLauncher** now has an opt-in, source-checked
guest profile for **isolated Fornex test endpoints**. The pinned upstream
hardcodes UDP 31314, WebAPI TCP 31315 and backend TCP 20443; isolated staging
uses UDP 32314, WebAPI TCP 32315 and backend TCP 21443. Without the profile,
local hosts and normal Yharnam Together clients keep the original behavior.
The remote guest profile requires a matching IPv4 host, explicit opt-in, valid
distinct ports and separate disposable credentials; alternate realms do not
receive automatic crash dumps. The portable ZIP contains **only a sanitized
example**, never users' real server profiles or private data.

[How to configure the developer-only server profile](tools/poc/yharnam/remote-profile-v46/README.md).
This is a **real BLauncher source change, not proof of working live
connections**. Direct P2P, lobby browser, invitations and password isolation
must still pass live two-client tests before public distribution.

## Game/launcher/server gates

The components that **must** become one complete, usable test bundle are:

1. [Windows native game CI](.github/workflows/shyt-v36-composed-windows-client.yml): compiles upstream Vulkan/game `bbport`, our code overlays and freezes **Yharnam Together BLauncher**, with the cooperative event patcher. Never includes proprietary game assets.
2. [Native Windows co-op server CI](.github/workflows/shyt-v41-win-qt683-server.yml): compiles and tests shadNet from the same pinned source with MSVC + Qt 6.8.3, stages Qt DLLs, configs and backend; **this is required by locally hosting BLauncher**.
3. [Actual Fornex staging server CI](.github/workflows/shyt-v39-fnx-ubuntu2404-qt683.yml): Ubuntu 24.04 + Qt 6.8.3 server with protocol/world/account/backend parity tests. **Separate staging only**, never replaces live production.
4. [Package and source checks](.github/workflows/shyt-mainline-source.yml): require correct game/launcher/server provenance, complete packages, game-derived event patch script, SHA-256 and exclusion of account secrets, saves and game assets.
5. **Still missing, mandatory before release**: real Windows install and run on GPUs, long multiplayer sessions, guest doors, NPC summon signs, death/revive/respawn, save recovery, mixed PS4/shadPS4/BBPort/CLS login and join, password matching/isolation, global sessions through Fornex, bandwidth/jitter/stability soak tests.

Direct P2P is **not** automatically PS4/CLS-compatible. Some native features are patches or opt-in only; a green source CI does **not** mean their in-game behavior is verified. The website is not a prerequisite for a basic playable co-op build.

**Do not install this candidate on the live Fornex instance or distribute it as a finished release.** Once those end-to-end gates pass, the target deliverable is simple: one staging-tested server archive + one complete Windows player bundle, update/rollback commands and a short Russian install guide for friends.
