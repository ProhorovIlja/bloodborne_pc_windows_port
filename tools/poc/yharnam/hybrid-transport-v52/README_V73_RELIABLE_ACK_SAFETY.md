# V73: GameLink reliable streams stay on shadNet until a real migration is implemented

**Status: source guard applied to the actual composed Yharnam Together game RX/TX. This is a reliability safety fix, NOT a completed Direct P2P session. No production Fornex changes.**

The pinned original Bloodborne GameLink / SHAD frame contains a common ACK number in its header and up to 80 unreliable or reliable native channel entries. Reliable channels are native 7..0x43, unreliable channels 0..6; ACK-only frames can have zero entries. Transferring only a gameplay packet without moving the associated reliable *sequence and ACK stream* risks stalls, drops, double-application, retransmits or desynchronization even if P2P UDP connectivity and HMAC authentication work.

V72's world authority and V70/V71's session checks are **necessary but not sufficient**: a boolean claiming reliable handover is verified does not actually migrate the native GameLink sequence/ACK/retransmission buffers.

## V73 behavior and performance scope

`sh_game_frame_offload.hpp::EligibleNativeWireFrame(..., native_reliable_handover_proven=false)` has a **fail-closed default**. It refuses Direct when the original wire frame contains:
- Any nonzero common ACK field, **including** an otherwise-unreliable movement packet piggybacking an ACK;
- Any packet of the reliable native class (including a frame that also has unreliable entries);
- A zero-entry native GameLink ACK-only/keepalive frame;
- Any existing authority/pair/role/map policy violation, malformed payload, spoofed sender or unrecognized channel.

The actual runtime `sh_direct_ingress.hpp` and `sh_native_direct_tx.hpp` explicitly call with `false` regardless of any optimistic world `reliable_stream_handover_verified` claim. This is important: even with an erroneous consent/grant flag, the real client cannot send or ingest reliable stream frames as Direct until we deliberately and separately wire an independently tested stream handover. For currently eligible authenticated **ACK-free unreliable** game frames, Direct selection is still governed by V66–V72 pair/room/world authorization, secure HMAC, three bidirectional signed probes, MTU, and server approval. Since there is still **no encrypted signaling/rendezvous and no Arm installer**, all actual game traffic still uses shadNet.

In real gameplay, a large fraction of packets may carry ACKs. Therefore this conservative guard limits any hypothetical CPU/egress savings until the reliable migration is solved. Do not invent throughput estimates.

## Real migration requirements before lifting the guard

1. Identify the precise original GameLink state per pair: sender/receiver instance, sequence, next expected, ACK, pending retransmit buffer and route epoch.
2. Perform a coordinated authenticated two-peer transition with exact session grant + world version and a recorded route epoch (including a deterministic point at which each side stops emitting/retransmitting on relay and begins doing so on Direct).
3. On route change, preserve ordering, ACK ownership and deduplication across BOTH SHLK and SHP1 paths. Delay route switch until full acknowledgement; use relay if transition cannot be proven.
4. Support NAT rebinding, route expiry/revocation, disconnect, temporary relay fallback, packet loss, duplicates, out-of-order and rapid oscillation. Never silently drop a reliable sequence or split a single native game frame between paths.
5. Complete two physical PC online stress tests and measure real server packets/CPU/egress and game RTT/jitter/frametime, not just synthetic policy tests.

## Tests

`test_game_frame_offload.cpp` directly exercises ACK-only, ACK piggyback, reliable and mixed SHAD frames with an authority that incorrectly claims the reliable handover is verified, and checks the default-deny API. `test_native_direct_tx.cpp` and `test_native_direct_rx.cpp` use real Windows CNG/Ubuntu OpenSSL HMAC and exercise the actual native send/receive policy. GitHub Actions `.github/workflows/shyt-v73-reliable-relay-safety.yml` runs all three suites on both platforms and checks the fully composed pinned original `p2p_sockets.cpp`/headers and SHA manifest, preserving the legacy shadNet `Link::EncodeData` fallback.

Never deploy this development source over the currently working CLS Friends live server or treat the long-running Windows renderer compile as already complete.
