// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V279: source-pinned original YT v1.3.1 Monocypher EdDSA/BLAKE2b
// signed server-issued ordered-pair grant. This is NOT a client-created
// opt-in bit and it does not invent a working NAT or matchmaking service.
//
// The verifier key MUST be pinned through the EXISTING authenticated
// shadNet LinkAuth server connection (or preconfigured independently).
// Never accept an authority key delivered by an unauthenticated peer.
//
// The issuer must separately check current TeamLobby membership, the
// original authoritative gameplay map/instances and peer endpoint.
// This is a cryptographic building block, not a production issuer.
#include "coop/link_auth.h"
#include "hybrid_peer_crypto_v241.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace BloodborneCoop::SHYTHybrid::SignedPeerGrantV279 {
using PubKey = std::array<u8,32>;
using SecretKey = std::array<u8,64>;
using Signature = std::array<u8,64>;
using Nonce = std::array<u8,16>;

struct Scope {
    std::string team, party, sender, receiver;
    u32 sender_instance=0, receiver_instance=0, map=0;
    u64 world_epoch=0;
    // POSIX wall-clock milliseconds. Server is responsible for bounded
    // clock skew; maximum lifetime is 30 seconds. Never use the
    // process-local steady_clock value as a cross-device timestamp.
    s64 issued_unix_ms=0, expires_unix_ms=0;
    // From server-verified LinkAuth addresses, in network byte order.
    u32 sender_ip_nbo=0, receiver_ip_nbo=0;
    u16 sender_port_nbo=0, receiver_port_nbo=0;
    // Responder's independently authenticated X25519 Noise key.
    PubKey responder_noise_pub{};
    Nonce grant_nonce{}; // 128-bit fresh OS CSPRNG, never constant in live.
    bool operator==(const Scope&) const = default;
};

struct Signed {
    Scope scope;
    Signature signature{};
};

inline bool NonZero(std::span<const u8> bytes) {
    return std::any_of(bytes.begin(),bytes.end(),[](u8 b){return b!=0;});
}
inline bool Valid(const Scope& g) {
    const auto named=[](std::string_view s,size_t cap) {
        return !s.empty() && s.size()<=cap &&
            std::all_of(s.begin(),s.end(),[](unsigned char c){
                return c>=0x21 && c<=0x7e; // no NUL/newlines in IDs
            });
    };
    return named(g.team,80) && named(g.party,96) &&
        named(g.sender,64) && named(g.receiver,64) &&
        g.sender!=g.receiver && g.sender_instance &&
        g.receiver_instance && g.world_epoch && g.map &&
        g.sender_ip_nbo && g.receiver_ip_nbo &&
        g.sender_port_nbo && g.receiver_port_nbo &&
        g.issued_unix_ms>0 && g.expires_unix_ms>g.issued_unix_ms &&
        g.expires_unix_ms-g.issued_unix_ms<=30000 &&
        NonZero(g.responder_noise_pub) && NonZero(g.grant_nonce);
}

inline std::vector<u8> EncodeScope(const Scope& s) {
    if (!Valid(s)) return {};
    std::vector<u8> bytes;
    bytes.reserve(5+2+80+2+96+2+64+2+64+82);
    const auto put=[&](u64 value,unsigned bits) {
        for(unsigned n=0;n<bits;n+=8)
            bytes.push_back(static_cast<u8>((value>>n)&0xff));
    };
    const auto str=[&](std::string_view value){
        put(value.size(),16);
        bytes.insert(bytes.end(),value.begin(),value.end());
    };
    bytes.insert(bytes.end(),{'S','H','G','P',1});
    str(s.team);str(s.party);str(s.sender);str(s.receiver);
    put(s.sender_instance,32);put(s.receiver_instance,32);
    put(s.map,32);put(s.world_epoch,64);
    put(static_cast<u64>(s.issued_unix_ms),64);
    put(static_cast<u64>(s.expires_unix_ms),64);
    put(s.sender_ip_nbo,32);put(s.receiver_ip_nbo,32);
    put(s.sender_port_nbo,16);put(s.receiver_port_nbo,16);
    bytes.insert(bytes.end(),s.responder_noise_pub.begin(),s.responder_noise_pub.end());
    bytes.insert(bytes.end(),s.grant_nonce.begin(),s.grant_nonce.end());
    return bytes;
}

// Server-only. The separate 64-byte EdDSA secret stays on the server.
// The 32-byte signing seed must be obtained from OS CSPRNG at deployment,
// not from a deterministic unit-test fixture or the existing X25519 key.
inline std::optional<Signed> Sign(const Scope& scope,const SecretKey& secret) {
    const auto bytes=EncodeScope(scope);
    if (bytes.empty()) return std::nullopt;
    Signed result{scope,{}};
    LinkMonocypher::crypto_eddsa_sign(
        result.signature.data(),secret.data(),bytes.data(),bytes.size());
    return result;
}

struct Expect {
    std::string_view team,party,sender,receiver;
    u32 sender_instance=0,receiver_instance=0,map=0;
    u64 world_epoch=0;
    // A real policy must compare requested route to the same pair,
    // NOT trust the signed grant as proof that the world has not changed.
};

inline bool Verify(const Signed& signed_grant, const PubKey& trusted_authority,
                   const Expect& live, s64 now_unix_ms) {
    const Scope& s=signed_grant.scope;
    if (!Valid(s) || !NonZero(trusted_authority) ||
        now_unix_ms<=0 || now_unix_ms>=s.expires_unix_ms ||
        now_unix_ms<s.issued_unix_ms-5000 ||
        live.team!=s.team || live.party!=s.party ||
        live.sender!=s.sender || live.receiver!=s.receiver ||
        live.sender_instance!=s.sender_instance ||
        live.receiver_instance!=s.receiver_instance ||
        live.map!=s.map || live.world_epoch!=s.world_epoch)
        return false;
    const auto bytes=EncodeScope(s);
    return !bytes.empty() &&
        LinkMonocypher::crypto_eddsa_check(
            signed_grant.signature.data(),trusted_authority.data(),
            bytes.data(),bytes.size())==0;
}
// V280: signed permission is not a Noise key. Both MUST bind to the
// exact same original YT sender/receiver, world run and responder
// static X25519 public key before a direct channel is even considered.
inline bool AuthorizesNoiseScope(
    const Signed& signed_grant, const PubKey& trusted_authority,
    const Expect& live, s64 now_unix_ms,
    const BloodborneCoop::SHYTHybrid::PeerCryptoScopeV241& noise_scope,
    const PubKey& responder_noise_pub)
{
    return Verify(signed_grant,trusted_authority,live,now_unix_ms) &&
        signed_grant.scope.party==noise_scope.party_session &&
        signed_grant.scope.sender==noise_scope.hunter_a &&
        signed_grant.scope.receiver==noise_scope.hunter_b &&
        signed_grant.scope.sender_instance==noise_scope.a_instance &&
        signed_grant.scope.receiver_instance==noise_scope.b_instance &&
        signed_grant.scope.world_epoch==noise_scope.world_epoch &&
        signed_grant.scope.map==noise_scope.map &&
        signed_grant.scope.responder_noise_pub==responder_noise_pub;
}

} // namespace BloodborneCoop::SHYTHybrid::SignedPeerGrantV279
