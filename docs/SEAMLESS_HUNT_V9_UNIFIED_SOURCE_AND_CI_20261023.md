# Seamless Hunt V9: reproducible native client/server source intake

**Date:** 2026-10-23. **Developer source gate only.** This is not a downloadable working Bloodborne client, nor a deployed Linux server.

## GitHub source of truth

- Verified developer binary input archives V3, V4, V5, V7 are committed at `tools/poc/yharnam/pinned-archives/`, byte-for-byte identical to the archived Drive assets (verified Git blob SHA-1).
- V8 update-channel generator and release protection remain at `tools/poc/yharnam/release-v8/`; no finished signed installer was published.
- Unified source composition script: `tools/poc/yharnam/unified-v9/compose_sources.py`. It enforces pinned Yharnam source SHA `77e350743a7cb4524cfcc1782fb6e3af64e25b15`, validates V3/V5/V7 archive SHA-256, combines DBNO V5 before UI scale V3 (same overlay source), and applies V7 native socket hooks plus V8 GitHub updater to a source-only output folder. It does not edit the original upstream checkout. It emits SHA-256 manifest and `public_release_ready=false`.
- V9 offline source-conflict tests: `tools/poc/yharnam/unified-v9/test_compose.py`. Locally checked a matching version of the tests, 5/5 PASS. Linux local V3 CTest 3/3 and V7 CTest 3/3 PASS (the V7 tests use real local UDP loopback).

## First actual GitHub CI entrypoint

The default branch `master` now contains **ONLY the read-only workflow** `.github/workflows/shyt-v9-source-gate.yml`, so `Actions → Seamless Hunt V9 native source integration → Run workflow` can be run manually. The workflow checks out **feature/yharnam-dedicated-server-poc**, validates tests, fetches the exact pinned Yharnam source, composes the unified source override, generates protocol-8 protobuf and, after success, attempts a real Ubuntu Qt6 `shadnet` build and the native `server_link`/`team_lobby` tests. On success it uploads **source-only** and **Linux server CI-only** artifacts. No secrets, production traffic, VPS changes or player packages are permitted.

**This workflow has NOT yet completed a GitHub Actions run.** Automated commits made by a connector can leave the Actions run list empty; do not claim a build or release before GitHub provides an actual green run. Manual dispatch is not the same as a public release.

Manual UI: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/workflows/shyt-v9-source-gate.yml

## Outstanding production blockers (priority order)

1. Port the V7 authenticated P2P candidate/peer consent and key exchange into real Qt shadNet control-plane and the native game's `p2p_sockets.cpp`, preserving ServerLink::Hub::Routed, BloodborneWorld::RoutesPacket and original virtual 10.x.y.z peer identity; V7 currently has dormant direct hooks ONLY. Implement drop/rekey/relay fallback securely before public deployment.
2. Make in-game Quick Play/lobby browser/filtered peer RTT/group invasion/DBNO rules use the real Qt server. V4 is a standalone tested logic layer, not the live WebAPI.
3. Build a **real Windows native bbport executable and launcher** with ALL these changes, test it with a protocol-8 server and at least two Windows clients, then with cross-NAT peers; only then allow GitHub Release publishing. Exact CUSA/version compatibility must be validated.
4. Real five-player character/game slot support, hostile-party gameplay, proper revive ownership, graphics/low-CPU performance, and 200-player load tests remain unverified.
5. Release an installer and a staged Linux server binary as a matched pair, keep server protocol release rollbacks, display changelog and automatic GitHub updates; never force users into manual VPN/ports/IP editing.

## Existing server DO NOT MODIFY

Fornex 199.195.193.131: running isolated legacy Yharnam Qt shadnet v7 PoC at `/srv/sh-yt-poc/stage-public-20261023` (UDP 32314, TCP 32315, 21443; localhost 32313) and separately production CLS on the 313xx family. No new V9 code has been installed there.

## Long-term handoff

Google Drive: https://drive.google.com/drive/folders/1_Yjz9ysS5mhL0mXUEoRqz0u3bjK6sIxM

Drive files were read successfully on 2026-10-23. Main document `00-START-HERE/START_HERE_NEXT_CHAT.md` was verified. Archives V3–V8 are on Drive; V3/V4/V5/V7 immutable blobs are also present in Git. Re-check HEAD and CI outcomes when resuming.
