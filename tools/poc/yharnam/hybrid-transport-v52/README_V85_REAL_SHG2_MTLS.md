# V85: real full-identity SHG2 over the original single Qt shadNet TLS listener

**Verified native source milestone, isolated loopback-only development integration. Direct gameplay and remote public TLS remain disabled.**

## What changed

- `sh_p2p_tls_key_session.hpp`: adds `SealOneLocalOfferV84` to the original V80 per-connection Qt TLS key session. Legacy SHG1 (`V81`) and full-width SHG2 (`V84`) share one `offer_sent_` guard, so a single authenticated TLS connection cannot mint both formats or repeat offers.
- `sh_p2p_tls_listener.hpp`: the original **same-process** Qt listener now accepts literal `YT-P2P/V84 OFFER\n` on an already TLS 1.3 mutual-authenticated session with an existing `V80 BEGIN`. Before issuing the offer it rechecks the certificate-bound current game account/epoch and queries a **server-owned**, mutually consenting current peer/world scope; the client does not supply any account, peer, IP or world authority. The old `V81` path still exists for the previous local test.
- `sh_native_tls_local_client_v85.hpp`: new C++20 non-Qt native OpenSSL/LibreSSL TLS client reusing V83's verified loopback socket and strict TLS transport. Accepts only authentic SHG2, verifies both **full** SHA256 game identities, current epoch/world/opt-in, expiry, mTLS server chain and 127.0.0.1 certificate IP SAN. Passes the bounded record to the V84 native sealed-grant inbox. On failure refuses, revokes pending and never arms Direct UDP.
- `unified-v9/compose_sources.py`: stages server and native game V84–V85 protocol headers into the pinned upstream source tree with SHA256 manifest. This only supplies sources: there is no native game runtime caller to the V85 TLS method and no automated connection.

## Verified CI, 25 October 2026

- [Actual native OpenSSL TLS 1.3 SHG2 client vs real Qt listener](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40233751312): PASS. Real loopback sockets and ephemeral CI-only CA/client certificates; validates the full 256-bit offer, expiry/epoch/current consent, wrong CA and revoked identity, while never arming gameplay.
- [Full pinned Qt shadNet server and preexisting V78–V83 mTLS regression](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40233751399): both CI jobs PASS, including compilation of the same original server code with new V84 source headers.
- [Pinned unified source composition/provenance](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40233751322): PASS.
- [V84 Windows CNG + Linux OpenSSL native receiver and Qt issuer tests](https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/40232130869): PASS.

## Hard release blockers

1. Enroll/rotate/revoke real TLS client credentials tied to the original native account system. Never ship the CI CA/private keys, no hardcoded public listener, no unauthenticated account claim.
2. Add the full SHG2 native identity to the original game-owned transport behind a safe disabled-by-default feature gate. Ensure reconnect/logout/world-change wipes pending grant and serial.
3. Authenticated rendezvous and **same existing game UDP socket** candidate exchange, signed reverse probes from both sides, NAT hairpin/symmetric NAT/CGNAT detection and rapid relay fallback.
4. Encrypt Direct gameplay datagrams and implement game frame/ACK sequence ownership handover before any Direct Arm. Do not send existing GameLink reliable/ACK traffic over split routes.
5. Real Windows EXE ZIP build, two-PC session/gameplay/latency/reconnect stress and measured server CPU/bandwidth reduction (up to ~200 players), before any public-release claim.

All current gameplay remains shadNet relay. Original single server and live Fornex CLS Friends, database, firewall, master, saves and player configurations are untouched.
