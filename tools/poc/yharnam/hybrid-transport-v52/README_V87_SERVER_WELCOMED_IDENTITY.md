# V87: original native game's accepted-account SHA-256 proof

Scope: **Yharnam Together only**, same P2PTransport and Qt shadNet. This is additive developer-only source under `SHYT_ENABLE_TEST_LOCAL_MTLS` (OFF by default); there is no gameplay UDP Direct activation or public remote TLS.

## What changed

1. `sh_native_game_identity_v87.hpp` hashes `YT-P2P-V84-ID:` + the **original game's** exact online ID bytes into the same full 32-byte SHA-256 digest as the V84 Qt server issuer. It uses Windows CNG or Linux OpenSSL, no 64-bit truncation. Empty, oversized, NUL or newline identities are rejected. A digest supplied by the caller is insufficient: the game must independently match its current own online ID.
2. `patch_native_link_identity_v87.py` performs an exact-source-anchored transformation after V86, within original native `P2PTransport`. The new developer-only local SHG2 call checks `running`, original `link_welcomed`, configured server endpoint, no artificial link cut, and the full digest against the current accepted native link ID.
3. The original game link tracks a monotonically increasing **developer-only** generation under `link_mutex`: every ConfigureLink (even the exact same online ID), build invalidation, new server Welcome or heartbeat quiet changes the generation. Zero or wrapped generation always denies. The V85 TLS response is rechecked against the same generation and current accepted link immediately before its test method returns; a changed generation revokes the pending SHG2 grant.
4. `unified-v9/compose_sources.py` stages the V87 header and fail-closed game source transform only after V82, V83, V84, V85 and V86 have composed. Existing SHG1 and relay operation remain intact.

## Threat boundary / remaining gates

**Important:** A `Welcome` on the existing upstream server link means this game was accepted into that connection; it does **not** constitute cryptographic proof of the server endpoint, arbitrary peer account, world/team state, or revocation. The full mTLS identity, authenticated Qt world consent and SHG2 cryptographic validation remain mandatory. V87 does not invent or trust a peer from local member messages and does not derive a world revision from client-reported data.

The native V85 call still has no automatic runtime invoker, still accepts world/peer state via a trusted callback requiring later audit, and has not been demonstrated in a real playable Windows EXE. Before Direct: pair both peers' authenticated account/session/world state, secure certificate enrollment and revocation, authenticated UDP rendezvous with both-way probes through the **existing** game socket, AES-encrypted datagrams, entire GameLink reliable/ACK lane handover and fast server fallback, measured two-PC and ~200-player load tests.

All modifications stay in draft PR #17. Working Fornex CLS Friends, server DB, master and saves remain untouched.
