# V94 upstream/fork audit, 2026-10-26

**Scope:** read-only inspection of *public source and PR descriptions* in CLSAMG22/BBSC, Amanises-Yharnam-Together/bloodborne-server, and lKaniel/bloodborne-server. All experimental source adaptations stay in draft PR #17 on feature/shyt-hybrid-p2p-v52. No Fornex deployment, live-master merge or save/account edits.

## Key result: an independently verified old pinned security bug

Our pinned original upstream source revision `77e350743a7cb4524cfcc1782fb6e3af64e25b15` in `server/src/stream_extractor.h` still contains the unsafe `m_pos + (int)size > m_data.size()` check in `getRawData`. A network-supplied `uint32_t` length above `INT_MAX` can become negative in the comparison, allowing an invalid out-of-bounds buffer access **before sign-in**. Upstream fixed it in **lKaniel PR #365**, and it is present in upstream `208c4f70718d1e73ef7deec2b4d3fdcc16ecce9a`.

Sources:
- https://github.com/lKaniel/bloodborne-server/pull/365
- https://github.com/lKaniel/bloodborne-server/blob/77e350743a7cb4524cfcc1782fb6e3af64e25b15/server/src/stream_extractor.h
- https://github.com/lKaniel/bloodborne-server/blob/208c4f70718d1e73ef7deec2b4d3fdcc16ecce9a/server/src/stream_extractor.h

**Implemented, unshipped in V94:** `patch_upstream_stream_bounds_v94.py` backports the EXACT three upstream checks (`getRawData`, `getBytes`, `peekBytes`) and its `Remaining()` helper into the pinned original Qt server, strictly rejecting source drift. `unified-v9/compose_sources.py` stages the patched server header by default. `test_stream_bounds_v94.cpp` verifies normal data, truncated blobs, malicious `0x7fffffff`, `0x80000000`, `0xfffffff0`, `0xffffffff` and negative fixed lengths. `shyt-v94-upstream-stream-bounds.yml` compiles against the *exact old pinned* upstream Qt source from GitHub after patch. **Do not claim CI PASS or shipping until verified.**

## CLS / Amanises 2026-10-25 change, not yet merged upstream

- Organization fork: https://github.com/Amanises-Yharnam-Together/bloodborne-server, branch `amanises-friends`, compared against its `main`: 2 commits / 47 files.
- Public author: CLSAMG22. PR https://github.com/lKaniel/bloodborne-server/pull/412, head `5dbf2dbb7e6ac66f5740cd444ef16417ca4f7e56`, **OPEN, not merged** at review time.
- Features actually visible in the PR patch: Friends list, friend requests, server-side username search, online-first, join invitations, three team-join policies (`INVITE_ONLY=0`, `ASK=1`, `OPEN=2`), listings and leader approval, team-size display. Protocol adds `TeamRequest` actions 16-24, new `LobbyState` 7-14 fields, new player relation fields, and a shared shadNet DB friend book.
- Important Leave/Remove bug: a departing member was previously invisible and camera-only, viewing a frozen host. PR #412 temporarily retains narrowly constrained **original game native channels** for 30 seconds after the cut so the leave packet reaches the host and the player loads their own world again. This is not just a UI fix. Verify no guest can revive old authority, cross worlds, or pass arbitrary non-native channels during this grace period.
- The PR adds explicit `RequireAuthenticatedIdentity()` in the original LinkServer and checks `Hello.member` against the logged-in account. Critical to preserve alongside friend search/joins; never trust client-supplied member names.
- Author reports original server tests and a two-person in-game test, but we have not independently rebuilt it or tested compatibility with our V84–V93 native session patch stack.

**Integration decision:** **ADOPT AFTER REBASE + VERIFIED TESTS, NOT BLIND CHERRY-PICK**. The PR changes 47 files across proto, UI, Qt server, database friends, world/party lifecycle, tests, 18 translation files and some GPU/packaging portability patches. Copying `coop.proto` or overlay alone can break game-server compatibility. First freeze protocol versions, add server-side access control/permission tests and logout/stop world transition tests, and separate unrelated FSR/Vulkan packaging edits from social features. No new DB or live service migrations without explicit tested rollback and separate user authorization.

## Other upstream candidates, prioritized

| Candidate | URL | Status / decision |
|---|---|---|
| Leader leaves and game host migrates | https://github.com/lKaniel/bloodborne-server/pull/403 | **High**. Real team ownership and session handover, potential conflict with CLS Leave fix. PR author reports tested 2-player scenarios; 3-player stress not all completed. Needs combined validation before integration. |
| Death spectate, opt-in team modes, free camera | https://github.com/lKaniel/bloodborne-server/pull/397 | **High**. User-requested controls and camera, server/proto/team sync & eboot hook sites. Not a simple graphics patch; opt-in and co-op compatibility must survive after world changes. |
| Boss-death spectate extension | https://github.com/lKaniel/bloodborne-server/pull/414 | **High after #397**. Requires spectator state and boss hook; upstream explicitly says stacked on #397. |
| Release/protocol compatibility warning | https://github.com/lKaniel/bloodborne-server/pull/417 | **Medium**. Reject different co-op protocol/release but WARN on different patches/mods/eboot. Good UX, but don't permit unsafe binary ABI divergence; requires server and game together. |
| Authenticated link and encryption | https://github.com/lKaniel/bloodborne-server/pull/375 | **Study, do not drop-in merge.** Noise NK + AEAD with pinned key; author says new wire protocol requires simultaneous rollout and game/emulator side had not been built at PR description time. It is separate from V84–V93 dev-only mutual TLS and the planned direct P2P gameplay encryption. |
| Sharding beyond 1000 players | https://github.com/lKaniel/bloodborne-server/pull/380 | **Defer** until tested original single-server hybrid Direct P2P path, 200-player baselines, player movement and shard directory failure cases. Early tests simulate players with loss and latency and admit game Redirect not tested. |
| V64 FSR Windows portability patches in CLS PR #412 | https://github.com/lKaniel/bloodborne-server/pull/412 | **Audit against PR #20 only**, not a second conflicting FSR patch stack. Independent portable `swprintf`, `_countof`, and mutex includes may complement our pinned Clang64 renderer work. |

## Discord screenshot vs verified source

The supplied Discord screenshots on 2026-10-26 show **BBSC** Rich Presence game invitations, a custom Bloodborne Seamless Co-op banner, and a Hunter's Dream party display with 1/4 playing. CLS public BBSC 0.0.2 release separately confirms Discord status enhancements, but the particular new join-invite/banner implementation shown in Discord is **not established by PR #412** and must not be declared merged into public BBSC or Yharnam Together without source/CI verification.

References: https://github.com/CLSAMG22/BBSC/releases and https://github.com/CLSAMG22/BBSC. Discord's official game-invites documentation states that invites rely on properly configured Rich Presence party and join secret, see https://github.com/discord/discord-api-docs/blob/main/developers/discord-social-sdk/development-guides/managing-game-invites.mdx.

**Follow-up recommendation:** optional Discord Rich Presence module only after native game state is truthfully available. Never disclose the user's game account password, direct NAT candidates, private IPs, TLS keying material, session token or a permanent join code in a public Discord secret. Use server-signed, expiring, revocable team invitations with correct privacy and capacity semantics. Discord invites cannot become proof of server authorization or Direct routing.

## Production isolation

- Do not merge CLS 47-file PR unreviewed into PR17; no original server transport/DB migration.
- Do not use deprecated shadPS4 or unrelated BBport gameplay as the native foundation: only port appropriate ideas and source-level fixes to Yharnam Together native/Qt.
- Production Fornex, original friends, master, game saves, player accounts and firewalls remain untouched.
- Direct game UDP still OFF, since signed NAT probes alone do not prove safe encrypted GameLink ACK ownership and failback.
