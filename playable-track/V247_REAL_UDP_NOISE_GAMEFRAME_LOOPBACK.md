# V247: actual kernel UDP socket roundtrip for original YT GameFrame

Date: 2026-11-01. Seamless Hunt playable track, Draft PR #85.

Unlike previous in-memory-only V240/V241/V243/V244 tests,
`test_hybrid_real_udp_loopback_v247.cpp` now opens three **real
Linux AF_INET/SOCK_DGRAM sockets** bound to 127.0.0.1, with bounded
receive timeouts and packet sizes.

## What runs

1. Hunter A creates a two-message peer Noise NK `Hello` using the real
   pinned YT 1.3.1 `LinkAuth::Noise` and sends it over an OS UDP socket
   to Hunter B. B receives it on a different socket, authenticates and
   sends an encrypted `Answer` back. A completes key agreement.
2. Independent derived A->B and B->A keys enter V241's genuine YT
   ChaCha20-Poly1305 `LinkAuth::Session`.
3. The actual original `GameFrame` is selected by V240, encrypted,
   transmitted over A->B UDP, received by B, authenticated and
   accepted by the V2 ingress gate, and passed to the **original**
   `GameLinkPeer::Receive`. A replay of the same packet is rejected.
4. An ACK piggybacked on native movement remains on a different
   physical UDP path through the separate test-only relay socket,
   preserving the same original `GameLinkPeer` receiver.
5. On lease expiry, further native movement moves back to the relay
   test socket instead of the direct socket, without changing native
   unreliable sequence numbers. Late old movement is deduplicated.
6. Existing `yt-playable-hybrid-policy.yml` now compiles and runs
   the V247 executable with published original upstream Monocypher,
   real Linux networking and no retail files or production credentials.

## Crucial boundaries

**Loopback does not prove internet/NAT traversal.** The test-only relay
forwards native frames directly; it is NOT the authenticated real
shadNet server, and it implements neither world authoritative routing
nor live resource management. Secrets are synthetic deterministic
test fixtures; real key generation/peer identities still need a
server-approved pair grant and OS CSPRNG.

The actual YT client send point is in
`emulator/src/core/bloodborne_patches.cpp`:
`peer.Flush(now_ms)` -> `EncodeGameFrame(frame)` -> SHAD
`GamePacketsType` -> existing client/server link. The V240–V247
helpers still need to be installed at this true send/receive point,
and the production client/server must negotiate trusted P2P grants
and STUN/ICE-like NAT reachability. Never switch on direct traffic
under an unauthenticated flag.

Real-world acceptance remains: separate Windows PCs, two and five
hunters, endpoint rebind, open/restricted/symmetric NAT, loss and
reordering, map changes, boss fights, invasions, late join,
disconnect/reconnect, and a measured decrease in Fornex egress/CPU
while keeping p99 join latency and world consistency within budget.

No private game binaries, real production keys, or Fornex changes
occurred in this stage; CI completion must be checked separately.
