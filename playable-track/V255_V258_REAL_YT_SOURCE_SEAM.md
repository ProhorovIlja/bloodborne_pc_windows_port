# V255–V258: real YT v1.3.1 game-client source hook, safe by default

Date: 2026-11-01. Draft PR #85. Not production deployed.

## Verified original source locations and invariants

Pinned official YT 1.3.1 commit
`5d2305ee611ef1e03be39ff925f0da75c9a70393`, SHA-1 Git
blob of `emulator/src/core/bloodborne_patches.cpp`:
`5e698a5bcd714f41ab40782a0838d63055d84d62`.

The actual `RunGamePacketLink()` does:
- ~line 1245: receives server-linked SHAD frames from
  `Libraries::Net::P2PGamePacketsRecvFrom`, decodes
  `GameFrame`, passes each one into **the one original**
  `GameLinkPeerOf(frame->sender).Receive`.
- ~line 1271: under `game_link.mutex`, collects each peer's
  `peer.Flush(now_ms)` and encapsulates it as SHAD/GamePacketsType.
- ~line 1305: **outside** `game_link.mutex`, sends those bytes using
  `Libraries::Net::P2PCoopSendTo`.

V255 introduces `yt_game_link_runtime_bridge_v255.h`: a bounded
`PendingYtFrameV255` plus `DispatchYtFrameV255` that:
- Sends exact original `SHAD` + `GamePacketsType` +
  `EncodeGameFrame(frame)` to the original shadNet address when
  no verified pair session is installed.
- When properly configured, composes the original V251 ACK coalescer,
  V240 Egress and real V241 YT ChaCha20-Poly1305 movement encryption
  with an external authenticated UDP send callback.
- Requires a live server-issued ordered-pair grant and crypto scope
  **for the same party, map and WORLD EPOCH** (V258).
- Requires explicit confirmation that a matching authenticated P2P
  receiver is attached to the ORIGINAL `GameLinkPeer` before offload.
- Leaves all reliable world data, team RPC, invasions and routing on the
  server. No second GameLinkPeer or separate native packet sequence.

V256 adds a **source-locked patcher** `apply_yt_game_link_seam_v256.py`:
- Verifies exact pinned upstream commit and original file Git blob
  before changing any source. All four expected anchors must be unique.
- `--mode check` is non-mutating; `--mode apply` copies the source
  headers into the YT clone and changes its real `RunGamePacketLink`
  send loop to this bridge. Frames are **moved**, not deeply copied,
  out of `game_link.mutex` and no socket I/O occurs under the lock.
- The actual patched call passes `nullptr` as trusted peer route.
  **ALL traffic remains on the original server** until a real
  authenticated grant registry, direct UDP sender and receiver are
  connected. This is an intentional production safety barrier.

To verify on a separate owner-owned source clone, NOT Fornex:

```sh
python playable-track/apply_yt_game_link_seam_v256.py \
  --upstream-checkout /path/to/yt131-source --mode check
```

The CI uses a disposable pinned-source checkout for `--mode apply`;
the applied source has not been proven to compile as the complete
retail YT game. The separate C++20 test
`test_yt_game_link_runtime_bridge_v255.cpp` links genuine upstream
Monocypher and `GameFrame` and covers the server-only path, a
verified movement path, ACK coalescing, direct transport failure,
`peer_instance=0` joining, missing direct ingress, wrong peer ID
and stale world epoch. There is no live multiplayer result yet.

## Hard gate before enabling direct mode

1. Server change: issue, authenticate, expire and revoke signed/AEAD
   scoped pair grants, including team-5/invasion eligibility.
2. Client change: real OS CSPRNG, Noise-NK exchange bound to those
   grants; authenticated STUN/NAT probing and endpoint rebinding.
3. Hook direct UDP Receive into the ORIGINAL
   `GameLinkPeerOf(frame->sender).Receive` **without** bypassing
   native channel/owner verification. Signaling and world actions
   always stay on the server.
4. Correct synchronization/lifetimes (map warp, disconnect, reconnect,
   team leader change) and no blocking socket calls inside game locks.
5. Test 2–5 actual PCs, multi-NAT classes, loss/reordering, boss
   fights, invasions, CPU/egress savings, p99 latency and rollback.
6. Compare BBHost v0.2.23 PR #199 GPU/memory changes, BBHost
   in-progress PR #200 SSR effects, YT PR #484 five-person team and
   #486 fifth-client load rig with license/ABI/source compatibility.

**Never claim the game has direct P2P or five-person online from these
source components alone.** No retail game assets or secrets in PR #85,
and no Fornex deployment.
