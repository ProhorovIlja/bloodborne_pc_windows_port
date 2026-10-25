# V70 actual P2P socket receive hook: source-backed, SAFE DEFAULT = RELAY

The patch `patch_native_direct_rx.py` is composed into the pinned Yharnam Together game process `emulator/src/core/libraries/network/p2p_sockets.cpp` **after V69**, not an external listener and not a new UDP protocol service on Fornex. It inserts `NativeDirectReceiver` into the **existing** `P2PTransport::ReceiveMain` physical UDP recvfrom loop.

## Packet flow after this source patch

```
P2PTransport::ReceiveMain receives UDP datagram on existing host_socket
  -> LinkCut / original firewall gates
  -> from configured shadNet server? dispatch original SHLK Data/Pong/etc
  -> looks like SHP1 direct UDP?
       -> no server-installed pair? DROP (current default)
       -> physical endpoint not exactly server-authorized? DROP
       -> world permission callback revoked? DROP and revoke link
       -> MAC bad, replay, expired, invalid peer binding? DROP
       -> signed Probe / heartbeat? consume to candidate liveness
       -> signed GameData with DirectReady and permitted complete SHAD frame?
            -> restore signed-grant-associated VIRTUAL sender addr/port
            -> original Deliver(virtual IP, virtual port, frame)
       -> everything else DROP
  -> all other UDP datagrams: existing Link::TakesDatagramFrom and Deliver path
```

**ShadNet relay is unchanged.** Real patched game uses the original physical UDP socket and original game vports; it never forwards raw/direct data from unrecognized peers to the game. The `NativeDirectReceiver` has **no runtime call to Arm** in the composed game, and will remain fail-closed until a new *authenticated encrypted* server control plane actually distributes and verifies grants, directional cryptographic secrets, NAT candidates, current world state and session consent. A preexisting plaintext SHLK Hello MUST NOT carry those secrets. HMAC authenticates but does not encrypt gameplay, so a final release must additionally handle confidentiality and privacy.

## Implemented now vs still missing

Implemented/tested:
- bounded 1,232-byte SHP1 direct wire datagram, HMAC callback and replay window;
- server-controlled role/map/owner authorization checked for the **entire** SHAD frame;
- up to 8 installed endpoints, currently zero, matched to exact physical IP+port;
- authenticated virtual source used for `Deliver()`, with no spoofed raw UDP source exposed to game;
- no-new-ports receive hook and protected per-peer receive state, automatic cleanup when physical game transport stops or server-link config changes;
- V70 unit suite with actual OpenSSL HMAC (Ubuntu) and Windows BCrypt (MSVC), known peer, unknown peer, bad tag, replay, expired paths, world revocation, unauthorized channels, bad inner game sender;
- source composition test on pinned native original, asserting no `direct_ingress.Arm(` call exists in game runtime.

Still release blockers:
1. **Authoritative peer identity and server-signed grants** rooted in the actual shadNet account/room/world DB, not user-supplied booleans or P2P probes.
2. **Authenticated encrypted transport** for signaling and short-lived directional secrets and revocations (TLS or other audited secure channel); plaintext server SHLK cannot distribute them.
3. **Real NAT traversal** candidate gathering/consent, CGNAT fallback with relay, strict privacy controls.
4. **Outbound** actual game socket hookup selecting Direct for all allowed channels and Relay for server-owned, dropped or unverifiable channels; preserve the complete native frame and tested GameLink sequence/ACK reliability across route switches.
5. Real native Windows executable, two physical PCs, loss/jitter tests, 2-hour sessions, cross-area and death/spectate QA.
6. **Measure** client/vps CPU, RAM, egress and packets/s at 2/5/20/200 players; V69 client submission counters are only a baseline, NOT server CPU savings.

Reference CI (V70): https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40207778743

Production safety: neither this source patch nor this README changes Fornex, current CLS Friends, systemd, firewall, game account DB, Python backend, or mainline master.
