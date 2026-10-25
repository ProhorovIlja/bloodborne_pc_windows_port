// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V88 DEV-ONLY: two-sided Qt server-issued SHG2 pair scope.
// Both inputs MUST be freshly captured from the ORIGINAL authoritative
// shadNet LinkServer->CaptureLocalP2POffer, once in EACH direction.
// Never use arbitrary client-submitted peers, world, endpoints or consent.
// This does not serve TLS, punch NAT, or arm any game socket.
#include "sh_p2p_tls_offer_v84.hpp"
#include <array>
#include <algorithm>
#include <cstdint>
#include <limits>

namespace SeamlessHunt::Hybrid {
struct P2PReciprocalOffersV88 {
    SecurePeerOfferV84 for_a{};
    SecurePeerOfferV84 for_b{};
};
class P2PReciprocalPairIssuerV88 final {
public:
    static bool Prepare(const P2PLocalOfferScope& to_a,
                        const P2PLocalOfferScope& to_b,
                        std::uint64_t now_ms,
                        SecurePeerOfferV84& out_a,
                        SecurePeerOfferV84& out_b) {
        // Both recipients must be server-authenticated and revalidated
        // immediately before issuing each separate TLS offer. This helper
        // cannot prove caller has actually done those checks.
        out_a={};out_b={};
        if(!now_ms || now_ms>(std::numeric_limits<std::uint64_t>::max)()-10000 ||
           to_a.recipient!=to_b.peer || to_b.recipient!=to_a.peer ||
           to_a.recipient==to_b.recipient ||
           to_a.recipient_epoch==0 || to_b.recipient_epoch==0 ||
           to_a.peer_epoch!=to_b.recipient_epoch ||
           to_b.peer_epoch!=to_a.recipient_epoch ||
           !to_a.world_revision ||
           to_a.world_revision!=to_b.world_revision ||
           !to_a.physical_ipv4_host || !to_a.physical_port_host ||
           !to_a.virtual_ipv4_host || !to_a.virtual_port_host ||
           !to_b.physical_ipv4_host || !to_b.physical_port_host ||
           !to_b.virtual_ipv4_host || !to_b.virtual_port_host)
            return false;
        // One public endpoint must not be assigned to two different
        // authenticated game accounts. Same WAN IP with different ports is
        // valid (two hunters behind the same NAT).
        if(to_a.physical_ipv4_host==to_b.physical_ipv4_host &&
           to_a.physical_port_host==to_b.physical_port_host)return false;
        const auto a=P2PFullIdentityIssuerV84::AccountDigest(to_a.recipient);
        const auto b=P2PFullIdentityIssuerV84::AccountDigest(to_b.recipient);
        if(!a || !b || !SecureOfferV84Detail::Nonzero(*a) ||
           !SecureOfferV84Detail::Nonzero(*b) ||
           SecureOfferV84Detail::EqualDigest(*a,*b))return false;
        std::array<std::uint8_t,40> random{};
        if(!SecureOfferV84Detail::Random(random))return false;
        std::uint64_t pair=0;
        for(unsigned i=0;i<8;++i)
            pair |= std::uint64_t(random[i]) << (8U*i);
        if(!pair || !SecureOfferV84Detail::Nonzero(
                std::span<const std::uint8_t>(random.data()+8,32))) {
            CryptoDetail::Erase(random);
            return false;
        }
        out_a.recipient_account=*a;
        out_a.sender_account=*b;
        out_a.session_epoch=to_a.recipient_epoch;
        out_a.world_revision=to_a.world_revision;
        out_a.pair_binding=pair;
        out_a.issued_ms=now_ms;
        out_a.expires_ms=now_ms+10000;
        out_a.peer_ipv4_nbo=qToBigEndian(to_a.physical_ipv4_host);
        out_a.peer_port_nbo=qToBigEndian(to_a.physical_port_host);
        out_a.peer_virtual_ipv4_nbo=qToBigEndian(to_a.virtual_ipv4_host);
        out_a.peer_virtual_port_nbo=qToBigEndian(to_a.virtual_port_host);
        out_b.recipient_account=*b;
        out_b.sender_account=*a;
        out_b.session_epoch=to_b.recipient_epoch;
        out_b.world_revision=to_b.world_revision;
        out_b.pair_binding=pair;
        out_b.issued_ms=now_ms;
        out_b.expires_ms=now_ms+10000;
        out_b.peer_ipv4_nbo=qToBigEndian(to_b.physical_ipv4_host);
        out_b.peer_port_nbo=qToBigEndian(to_b.physical_port_host);
        out_b.peer_virtual_ipv4_nbo=qToBigEndian(to_b.virtual_ipv4_host);
        out_b.peer_virtual_port_nbo=qToBigEndian(to_b.virtual_port_host);
        // V89: both recipients receive the SAME fresh pair secret, but only
        // inside their independent SHG2-over-mTLS wrapping keys. Each
        // native peer derives independent A->B/B->A PROBE and GAME keys
        // with DirectionKeyScheduleV89. NEVER install this raw secret
        // directly as a UDP MAC/AEAD key.
        std::copy_n(random.begin()+8,32,out_a.direction_key.begin());
        std::copy_n(random.begin()+8,32,out_b.direction_key.begin());
        CryptoDetail::Erase(random);
        if(!SecureOfferV84Detail::Valid(out_a,now_ms) ||
           !SecureOfferV84Detail::Valid(out_b,now_ms)) {
            CryptoDetail::Erase(out_a.direction_key);
            CryptoDetail::Erase(out_b.direction_key);
            out_a={};out_b={};
            return false;
        }
        return true;
    }
};
} // namespace SeamlessHunt::Hybrid
