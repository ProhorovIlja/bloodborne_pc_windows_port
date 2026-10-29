# V82: real native game owns a zeroizing, replay-rejected sealed P2P offer inbox

**Developer/source-only, NOT a working remote native-game TLS client or Direct P2P gameplay connection.** Only Yharnam Together's native P2PTransport is targeted; not shadPS4, bbport or Supermedo interop. Production Fornex CLS Friends remains unchanged.

## What was actually integrated

- Added portable C++20 `sh_native_grant_inbox.hpp`, relying on the same V75 `sh_secure_grant.hpp` AES-256-GCM implementation (Windows BCrypt CNG, Linux OpenSSL EVP) already staged on both native game and the Qt server. This is not Qt-dependent, so it can compile within the native Windows/Linux game process.
- V82 `patch_native_grant_inbox.py` modifies the ACTUAL original pinned `emulator/src/core/libraries/network/p2p_sockets.cpp` after V71. A `NativeSealedGrantInbox` lives as a private field of the existing `P2PTransport` with its own mutex. Its key and pending peer offer are revoked/cleared on the two original transport lifecycles: server UDP socket stop and shadNet account/server link replacement. One OS UDP socket, original SHLK relay and current network-packet routing all remain unchanged.
- `unified-v9/compose_sources.py` stages the new header alongside original game's actual network code. NO `NativeDirectReceiver::Arm`, `NativeDirectSender::Arm`, TLS socket, HTTP connection, peer IP logging, NAT probe or synthetic game account is added to the game runtime.

## Portable native recipient protocol

`NativeSealedGrantInbox::BeginTrustedTls(key, expected, tls_serial, refresh, owner)` must be called ONLY by a FUTURE properly authenticated TLS 1.3 native client adapter that has validated the server certificate and hostname/pin, linked the local game online ID to the current signed-in account, received the V80 **new connection-specific** 32-byte wrapping key, obtained recipient/sender tokens from trusted authenticated matchmaking, and fetched the current authoritative game epoch/world. It rejects invalid/duplicate or non-monotonic local connection serials, absent peer identity, no local opt-in, and unreachable/revoked current game authority.

`ReceiveSealedTlsLine` accepts **exactly one** `YT-P2P/V81 OFFER <270 hex digits>\n` record from that *TLS stream* (never game UDP, never plaintext SHLK, never local JSON). It performs strict length/prefix/hex decoding, V75 AES-256-GCM tag authentication, nonce replay rejection, 10s grant expiry, recipient token, expected sender token, session epoch, world revision and mandatory physical/virtual peer endpoint checks; it then checks the live game authority AGAIN before staging. Wrong key, spoofed peer, stale epoch/world, changed local opt-in, malformed or replayed offer fail closed and zero decrypted keys.

A pending offer remains UNARMED. `HasCurrentPending` and `PendingForNat` re-check live world/opt-in/time before showing it to a future verified NAT candidate exchange. A new server/account change destroys the pending direction key. No method can enable direct game traffic: before doing that, implement the real client TLS 1.3 adapter, trusted key/identity enrollment, bidirectional mutually confirmed grants, NAT candidate holepunch over existing native UDP socket, 3 authenticated reverse probes and packet encryption, then coordinate native GameLink reliable stream seq/ACK/retransmit handover. CGNAT and invalid routes stay on the original shadNet relay.

## Evidence and CI

`test_native_grant_inbox.cpp` exercises the actual V75 SHG1 AES ciphertext under GCC/OpenSSL and Windows MSVC/CNG with production-equivalent native header. Covers all fields, local opt-in revocation, different game world after reconnect, expiry boundary, replay, wrong recipient/peer/epoch/secret, unsupported malformed/tampered hex/prefix/length, missing current authority and secure reinitialization.

`.github/workflows/shyt-v82-native-grant-inbox.yml` compiles and executes on **Windows-2022 MSVC, Ubuntu 24.04 GCC/OpenSSL**, and composes the exact original pinned game plus native inbox, checking source SHA and two lifecycle-revocation hooks and proving no installer or Direct Arm call exists yet.

Also `test_tls_local_offer.cpp` in the V78–V81 Qt/OpenSSL mTLS suite now passes the **actual encrypted bytes received from an authenticated TLS 1.3 socket** into the identical portable `NativeSealedGrantInbox`. This is a valuable whole-wire interoperability test, but the test harness is a Qt dev client, NOT the native PC game's future TLS adapter.

### Known barriers and safety

The V75 SHG1 developer wire uses 64-bit truncated account tokens, not full authenticated 128/256-bit canonical account identifiers; token collisions and account enrollment must be resolved before public release. The V82 API cannot itself prove TLS authenticity; caller must supply verified context from an authenticated TLS adapter, which is not present in the composed native game yet. HMAC SHP1 game datagrams remain unencrypted, and V73 continues to route any reliable/ACK-piggyback game frame through shadNet. No P2P throughput gain or 200-player load improvement is claimed yet, and no production Fornex port/db/systemd changes are part of this patch.
