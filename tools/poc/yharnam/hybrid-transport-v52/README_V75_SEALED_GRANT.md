# V75: recipient-authenticated, confidential, replay-rejected P2P offers

**Status: Windows CNG + Ubuntu OpenSSL AES-256-GCM cryptographic source component with actual full candidate composition. NOT a live TLS signaling service, client installation, encrypted gameplay, or active Direct P2P.**

The V74 co-op Hello provides explicit consent by both players, and V72 scopes the current candidate to the server's actual world, party and map. V75 adds the *recipient-specific secure offer serialization* needed before any endpoint or per-direction gameplay MAC key can be delivered.

## Cryptographic contract

- Algorithm: AES-256-GCM authenticated encryption (Windows BCrypt/CNG or Ubuntu OpenSSL EVP), random 96-bit nonce from OS CSPRNG on EVERY offer, 128-bit AEAD tag.
- No plaintext endpoints or traffic MAC key appear in the sealed wire format. Sender/recipient account IDs, world revision, session epoch, pair binding, issue/expiry timestamps, both physical and virtual IPv4+port, and fresh **direction-specific 256-bit UDP HMAC key** are covered by the ciphertext+tag.
- Mandatory domain separation: fixed `YT-P2P-GRANT-V75` associated data; versioned bounded `SHG1` envelope, exactly 135 bytes. Unknown version/length, altered header/ciphertext/nonce/tag, wrong TLS-exporter channel key, wrong recipient/session/world, invalid identity, invalid ports, malformed/zero direction secret, future-issued or expired grant, or TTL over 30 seconds => reject.
- Replay rejection occurs only after a successful AEAD tag check, before the grant can be used. A fixed maximum 64 accepted offers per **single** exporter key is enforced **fail closed** (no nonce evictions; rekey the authenticated control channel). Channel key material and decrypted staging buffers are explicitly zeroed on cleanup/failure.
- The eventual control channel must authenticate the server and the **intended recipient account** over TLS 1.3 and deliver a context-separated exporter key unique to that channel/session. A 32-byte value given to `InstallChannelKey` is a **precondition**, not proof of TLS or verified identity. In particular do not reuse an exporter between sessions or set it to any static value; never derive it from a Bloodborne password or legacy plaintext shadNet Hello.
- A grant's world revision is a *version*, not a signature. Before any actual `Arm()` call, the future TLS grant installer **must re-check the current server-authoritative V72 world/party, V74 mutual consent, session generation, expiration, and account identity**, including revocation. Server alone must mint the grant and the direction key.

## Source integration

`sh_secure_grant.hpp` is staged in the fully pinned composed **native game** at `emulator/src/core/libraries/network/sh_secure_grant.hpp` and original Qt server at `server/src/sh_secure_grant.hpp`; the server also stages `sh_direct_crypto.hpp` and `sh_direct_datagram.hpp` as shared dependencies. This is common source, not a separate Python gameplay server, extra UDP relay, or service process. It DOES NOT register an HTTP endpoint, listener, TLS acceptor, issue a secret, or call `NativeDirectSender::Arm` / `NativeDirectReceiver::Arm`. This is intentional: the existing `shadNet` HTTP and SHLK signaling are not an encrypted/authenticated key-distribution transport.

The planned single Qt server must expose a **secured, separately authenticated TLS signaling path on the SAME SERVER DAEMON** (not two side-by-side game servers), or reuse a demonstrably authenticated encrypted channel. No peer candidate is disclosed or client game Direct-enabled before mutual consent and independently verified server/world state. Add rate limits, session-bound revocation and privacy choices. For NAT/CGNAT failures, keep the existing shadNet relay.

## CI and limitations

`.github/workflows/shyt-v75-sealed-peer-grants.yml` compiles and executes `test_secure_grant.cpp` on real Windows MSVC with BCrypt and Ubuntu GCC with OpenSSL, covering AES roundtrip, non-identical random nonces, refusal of plaintext key leakage, wrong recipient/epoch/world, expiry/TTL, tampered envelope/tag, truncation, wrong secret and replay cache exhaustion. Full pinned original Qt+game composition checks matching common code and no live `Arm` call in game.

HMAC-signed `SHP1` game UDP from V70/V71 is **not encrypted** and this V75 grant codec does **NOT** make gameplay confidential. Public P2P requires protecting game contents and player IP privacy expectations separately. V73 still keeps reliable/ACK-piggyback frames on shadNet until actual GameLink ACK/sequence handover, so do not assume all game traffic can be offloaded.

There is no demonstrated 2-PC direct game connect, player count/performance improvement, live Fornex migration, deploy ZIP, or production permission to switch Direct. No live CLS Friends account DB, shadNet unit, firewall, or GitHub master modification here.
