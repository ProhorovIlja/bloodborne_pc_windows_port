# Seamless Hunt V8: GitHub update channel and matched server deployment

Status (2026-10-23): developer sources only. NOT a tested public Bloodborne client/server release.

The pinned Yharnam Together launcher already has a user-facing Update button, sha256-checked setup download, and a Home patch-notes UI. Our fork reuses it.

- Launcher: tools/poc/yharnam/release-v8/patch_update_channel.py changes the coop GitHub releases source to numeric repo ID 1429375055, accepts only tags shyt-vX.Y.Z, keeps changelog from release body, and requires an installer, SHA256, release manifest, and claimed server protocol 8 / link protocol 2.
- Safety: the downloaded installer must match both GitHub release SHA256 asset and manifest installer SHA256. The independent upstream native BBPort updater is disabled only inside our fork to prevent unrelated engine updates.
- Build: tools/poc/yharnam/windows-oneclick/patch_and_freeze.py now accepts --release-channel. The one-click Windows CI workflow uses this and marks the test artifact version 0.0.1-dev.1. This freezes a launcher, NOT a tested full native gameplay runtime.
- Release gate: tools/poc/yharnam/release-v8/release_gate.py refuses matched release manifest generation without same-pinned-source client and server binaries, matching SHA256 and actual two-PC join, DBNO, P2P, fallback, ping, staging, health and rollback evidence.
- Server: tools/poc/yharnam/release-v8/STAGE-FORNEX-RELEASE.sh stages a reviewed Linux binary to a new /srv/sh-yt-releases/<version> directory. It does not touch production CLS, current Yharnam services, DNS, firewall or existing saved games.
- CI: .github/workflows/shyt-release-v8-ci.yml checks the updater source transforms against the real pinned Yharnam Together tree. Successful GitHub Actions execution has NOT yet been confirmed.

Release sequence: (1) compile integrated native Windows gameplay engine and Qt shadNet server, (2) test Direct P2P signaling, packet authentication, interest/channel filtering and relay fallback across real NATs, (3) test five-player changes only after runtime slots really work, (4) stage on separate Fornex ports with rollback, (5) activate matched server and verify, (6) issue a reviewed shyt-vX.Y.Z GitHub Release containing setup.exe, matching checksum, release manifest and changelog. Only then distribute the one-click client.

The upstream lobby is still four-player and all-game-data-through-server; V7 direct P2P socket prototype and V5 DBNO source patch have NOT yet been combined into a gameplay-tested binary. GitHub release manifest alone is not a cryptographic signature or live server health proof.

Local developer artifact SH-YT-RELEASE-UPDATER-V8-20261023.zip (5/5 offline unit tests and Bash syntax check pass). Neither deployment nor release publishing has occurred.
