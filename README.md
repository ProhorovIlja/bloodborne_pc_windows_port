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

## Game/launcher/server gates

The components that **must** become one complete, usable test bundle are:

1. [Windows native game CI](.github/workflows/shyt-v36-composed-windows-client.yml): compiles upstream Vulkan/game `bbport`, our code overlays and freezes **Yharnam Together BLauncher**, with the cooperative event patcher. Never includes proprietary game assets.
2. [Native Windows co-op server CI](.github/workflows/shyt-v41-win-qt683-server.yml): compiles and tests shadNet from the same pinned source with MSVC + Qt 6.8.3, stages Qt DLLs, configs and backend; **this is required by locally hosting BLauncher**.
3. [Actual Fornex staging server CI](.github/workflows/shyt-v39-fnx-ubuntu2404-qt683.yml): Ubuntu 24.04 + Qt 6.8.3 server with protocol/world/account/backend parity tests. **Separate staging only**, never replaces live production.
4. [Package and source checks](.github/workflows/shyt-mainline-source.yml): require correct game/launcher/server provenance, complete packages, game-derived event patch script, SHA-256 and exclusion of account secrets, saves and game assets.
5. **Still missing, mandatory before release**: real Windows install and run on GPUs, long multiplayer sessions, guest doors, NPC summon signs, death/revive/respawn, save recovery, mixed PS4/shadPS4/BBPort/CLS login and join, password matching/isolation, global sessions through Fornex, bandwidth/jitter/stability soak tests.

Direct P2P is **not** automatically PS4/CLS-compatible. Some native features are patches or opt-in only; a green source CI does **not** mean their in-game behavior is verified. The website is not a prerequisite for a basic playable co-op build.

**Do not install this candidate on the live Fornex instance or distribute it as a finished release.** Once those end-to-end gates pass, the target deliverable is simple: one staging-tested server archive + one complete Windows player bundle, update/rollback commands and a short Russian install guide for friends.
