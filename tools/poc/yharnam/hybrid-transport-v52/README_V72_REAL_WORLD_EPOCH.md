# V72: server-owned Bloodborne world revision for future P2P grants

**Status: actual Qt shadNet server source and original tests patched, compiled and executed. NOT deployed; no Direct P2P session is enabled.**

The pinned original `BloodborneWorld::Service` owns each player's current party and map, the open-world epoch, map reset timestamps, session run and enemy-area owner. These are not client-provided P2P "verified" flags; they already serve gameplay routing via `RoutesPacket`.

`patch_live_world_epoch.py` adds `Service::DirectWorldEpoch(source,destination)` to `server/src/bloodborne_world.{h,cpp}`. It returns **zero** when a player is unknown, outside the party, deleted/cut from the team, still loading, on a different map, the world is unavailable, or the pair is identical. Otherwise it combines current server world epoch, map-reset marker, session run, both maps, and current area-enemy owner using a small bounded deterministic non-secret fingerprint.

The *real* Qt `LinkServer` now installs `m_link.SetDirectWorldEpoch(...m_world.DirectWorldEpoch(...))` to feed V67's preexisting internal `Hub::CaptureDirectPairSnapshot()` and `ValidateDirectPairSnapshot()`. The game world's version can therefore revoke a pending/issued **internal** candidate snapshot when its room/map/owner/world state changes. Existing V66 signed-in + same-party + mutual-consent gates still apply.

**WARNING:** the 64-bit fingerprint is not a MAC, not an authorization token, not a cryptographic digest, and not suitable for peer/client trust. Changes that revert exactly to a previous world/owner signature could reproduce a value. A future public secure grant must also carry the server's monotonic session generation/revocation revision and be signed/bound to mutually authenticated identities and ephemeral keys. Existing snapshots have a maximum 5-second lifetime. Do not perform server per-packet version lookup; do this only on candidate/grant issuance and renewal. There is still **NO** production consent provider, credential grant delivery, encrypted rendezvous, or NAT candidate negotiation, so the server continues to refuse live Direct establishment.

Tests:
- `test_world_revision.cpp` confirms stable/changed values, different map and no-team defaults on MSVC Windows and GCC Ubuntu.
- Modified pinned **original** `server/tests/test_bloodborne_world.cpp` checks no map, same-map pair, different-map pair, unknown endpoint and removed team member.
- CI actually builds, **links and executes the original Qt/protobuf world tests** with the composed V72 server code, and checks the true `link_server.cpp` C++ syntax against Qt6 headers. The full shadNet daemon was **not** built, installed, restarted or deployed.
- Passing workflow: https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40210674520

The current Fornex CLS Friends production binary/database remain untouched. The long-running Windows *client renderer* build is independent. Next release blockers remain a properly authenticated encrypted signaling/control plane (NOT old plaintext SHLK UDP or HTTP), fresh key generation/directional derivation and client session-arm logic, NAT traversal, reliable game stream switching, two-machine game QA, and server CPU/egress benchmarking.
