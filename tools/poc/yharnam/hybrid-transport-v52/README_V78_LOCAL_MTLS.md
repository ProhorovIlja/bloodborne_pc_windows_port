# V78: real Qt TLS 1.3 **local** rendezvous readiness on the same shadNet executable

**Status:** real `QSslSocket`/OpenSSL encrypted mTLS connection, composed into the original pinned `server/src/main.cpp` (same one Qt shadNet process). It is a **developer-only, loopback-only readiness endpoint** with no secure grant issuance and no P2P traffic offload. Not deployed to Fornex.

## Why this approach

The original server has plaintext SHLK UDP/TCP and an HTTP WebAPI. Neither should ever carry another player's real IP address, session keys, or peer grant. The V75 `SHG1` AES-256-GCM encrypted grant codec also requires a genuinely authenticated encrypted delivery channel.

Qt 6.4 (the pinned CI environment) supports `QSslSocket::startServerEncryption()` but **does not have Qt 6.12's TLS exporter/keying-material API**. We therefore must NOT pretend that a Qt 6.4 session already supplies the `InstallChannelKey` secret required by V75. This version deliberately **does not call that API or issue any SHG1 grants**.

## Real changes

- `sh_p2p_tls_listener.hpp` implements a bounded `QTcpServer` with per-connection `QSslSocket`, TLS **1.3 only**, certificate-chain verification with a configured trusted *client* CA, rejection of missing/bad client certificate, maximum 32 concurrent connections, 5-second timeout, maximum 64 input bytes and no TLS-to-plaintext downgrade.
- Only the exact fixed command `YT-P2P/V78 STATUS\n` yields `YT-P2P/V78 TLS_READY NO_GRANTS\n`. Unknown, oversized and unauthenticated input disconnects; **no game accounts, world IDs, peer IPs, grant keys or other secrets** are exchanged.
- `patch_tls_local_listener.py` patches the actual original Qt `server/src/main.cpp` after its original shadNet server startup. An instance lives **in that same main process**; there is no second game server. By default the endpoint doesn't exist. If the exact `SHYT_P2P_TLS_LOCAL_TEST=1` flag is supplied, startup requires a valid certificate, key and client CA. Failure aborts startup rather than silently downgrading. It always binds `QHostAddress::LocalHost` (127.0.0.1), never a public interface.
- No changes to CLS Friends, shadNet DB, player profiles, existing firewall, Fornex ports or normal shadNet SHLK routing. This is optional source code inside an **undeployed** development build.

## Optional local dev settings (only on throwaway offline test machine)

```
SHYT_P2P_TLS_LOCAL_TEST=1
SHYT_P2P_TLS_SERVER_CERT=/path/to/temporary/server.pem
SHYT_P2P_TLS_SERVER_KEY=/path/to/temporary/server.key
SHYT_P2P_TLS_CLIENT_CA=/path/to/temporary/dev-only-ca.pem
SHYT_P2P_TLS_LOCAL_PORT=0
```

Port `0` requests an ephemeral OS port; startup logs the bound local address and port. **Never set these test variables on the live Fornex service, never deploy production CA keys to players, and never reuse the CI certificate authority.** CI creates temporary RSA leaf certificates during the test, not in the repository.

`.github/workflows/shyt-v78-mtls-local-control.yml` compiles and runs an actual Qt TLS 1.3 loopback handshake with a CA-signed server and client certificate, checks no-client-cert failure, then composes the original full shadNet source and syntax-compiles its real `main.cpp` with Qt + protobuf. Separately checks the listener remains disabled without explicit environment variables.

## Next blockers for actual encrypted gameplay grants

1. Certificate issuance/provisioning and **cryptographically verified binding** of authenticated TLS client identity to the same current signed-in game account and game-session epoch. A CA-trusted client certificate alone does NOT prove it owns any specific Bloodborne game session.
2. Secure mTLS control protocol with bounded requests, replay/rate limiting, server-only generation of fresh per-direction HMAC keys, server-side V76/V77 scope recheck and explicit current mutual consent. Qt 6.4 lacks the high-level TLS exporter. Use audited OpenSSL TLS exporter support (with portable Windows backend design) or a distinct, authenticated TLS-protected application key exchange with explicit domain separation; do NOT inject static shared keys.
3. Only after the above, mint recipient-bound V75 encrypted grants, client verify/revoke, NAT candidates from the original game socket, and actual TX/RX `Arm` calls. Handle CGNAT with existing relay.
4. Encrypt gameplay contents separately: `SHP1` HMAC only authenticates gameplay; V75 grant encryption alone does not encrypt game packets.
5. Full GameLink reliability/ACK route handover, two actual native game clients and measured Fornex load at 200 players.

No claim is made that Direct P2P currently works or that the Windows native renderer build is already complete.
