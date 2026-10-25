# V74: Real Yharnam Together native game-to-server mutual P2P opt-in

**Source-only development. NOT a live Direct P2P deployment or secure key exchange.** Only Yharnam Together/native port is targeted. Production CLS Friends Fornex server remains unchanged.

## Implemented in actual pinned source

1. Added optional `bool direct_p2p_opt_in = 7` to the existing native and server **shared protobuf** `server/coop/coop.proto::Hello` message. This is compatible with old protobuf clients: missing value defaults to false. No protocol version change needed, because wire parsing of an optional scalar is backward compatible.
2. In `emulator/src/core/bloodborne_server_world.cpp`, the native-port-only cooperative world Hello now includes the opt-in setting iff `SHYT_DIRECT_P2P_OPT_IN=1` is set in the process environment. Default absent or any other value is false. shadPS4/non-native branches do not set it. This is only a developer switch pending launcher settings; it is not a P2P enable button and **does not trigger any Direct UDP session**.
3. The existing actual Qt `BloodborneWorld::Service::Member` stores this explicit flag **per current authenticated game link**, clearing it on each new/refused Hello and when that link is forgotten. `PairDirectConsent(a,b)` looks up the server-verified SHLK `online_id` identities, rejects duplicate IDs, missing/legacy consent, mismatched/currently cut team, no map/loading and different maps, using V72's actual world revision as the final grant-scoping check. It does no per-game-packet work.
4. Actual Qt `LinkServer` installs `m_link.SetDirectConsent(...m_world.PairDirectConsent(...))`. V66's pair gate can thus evaluate BOTH directions. A rogue guest cannot authorize peers by setting a flag only for themselves.
5. Original `server/tests/test_bloodborne_world.cpp` now covers: two players same map but unilateral opt-in rejected; both opt in accepted; unknown and self pair rejected; loading map revokes; next map update recovers; explicit opt-out revokes; removal/forget revokes. The original Qt+protobuf world tests compile against the NEW composed co-op proto, not the unpatched original pinned proto.

## Critical security boundary

The flag is **user preference**, not authentication, encryption, permission for sharing credentials or proof of a reachable Direct socket. Qt server already authenticates each game account at its SHLK Hello; the shared game Coop Hello rides in that authenticated link's session. Before any IP addresses or keys are revealed, a future new server/client control path **must** provide: mutual TLS-authenticated encrypted rendezvous, server-signed short-lived pair/session/map grants and revocations, ephemeral per-direction secrets, NAT candidate/consent exchange and official UI preference (e.g. off/on or privacy mode). **Never distribute peer secrets/addresses via existing plaintext SHLK or WebAPI HTTP.**

Until that exists, **the original shadNet relay is used exclusively**, despite an opt-in. The existing native Direct TX/RX still have zero Arm calls in the composed game runtime. Preserve reliable GameLink fallback from V73.

Any dev experiment should use a throwaway private server and accounts, never the live Fornex usernames/passwords. No new production sockets, ports, firewall edits, or database migrations are included here.
