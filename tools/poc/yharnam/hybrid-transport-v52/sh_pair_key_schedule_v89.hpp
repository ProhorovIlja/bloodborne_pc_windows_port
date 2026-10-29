// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V89: directional key schedule for V88 paired SHG2 offers.
// The two recipients receive the SAME 32-byte CSPRNG pair master wrapped
// separately by mTLS+AES-GCM. Derive four distinct keys, never authenticate
// UDP with the raw master or confuse NAT probes with gameplay data.
// This is a pure C++20 helper, NOT an active UDP socket.
#include "sh_secure_grant_v84.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <span>

namespace SeamlessHunt::Hybrid {
enum class PairKeyPurposeV89 : std::uint8_t { NatProbe=1, GameData=2, ReadyProof=3 };

class PairKeyScheduleV89 final {
public:
    static bool Derive(const SecurePeerOfferV84& grant,
                       bool outbound,PairKeyPurposeV89 purpose,
                       std::uint64_t now_ms,
                       std::array<std::uint8_t,32>& result) noexcept {
        result.fill(0);
        if(!SecureOfferV84Detail::Valid(grant,now_ms) ||
           (purpose!=PairKeyPurposeV89::NatProbe &&
            purpose!=PairKeyPurposeV89::GameData &&
            purpose!=PairKeyPurposeV89::ReadyProof))
            return false;
        // Grant is recipient-perspective: sender_account is peer,
        // recipient_account is this native game. Reverse for outgoing.
        const auto& from=outbound ? grant.recipient_account
                                  : grant.sender_account;
        const auto& to=outbound ? grant.sender_account
                                : grant.recipient_account;
        static constexpr char domain[]="YT-P2P-V89-PAIR-DIRECTION";
        std::array<std::uint8_t,sizeof(domain)-1+1+32+32+8+8> input{};
        std::size_t at=0;
        for(std::size_t i=0;i<sizeof(domain)-1;++i)
            input[at++]=static_cast<std::uint8_t>(domain[i]);
        input[at++]=static_cast<std::uint8_t>(purpose);
        for(auto b:from)input[at++]=b;
        for(auto b:to)input[at++]=b;
        for(unsigned i=0;i<8;++i)
            input[at++]=static_cast<std::uint8_t>(
                grant.pair_binding >> (8U*i));
        for(unsigned i=0;i<8;++i)
            input[at++]=static_cast<std::uint8_t>(
                grant.world_revision >> (8U*i));
        const bool ok=at==input.size() &&
            CryptoDetail::Sha256Hmac(grant.direction_key,input,result);
        CryptoDetail::Erase(input);
        if(!ok)result.fill(0);
        return ok;
    }
};
} // namespace SeamlessHunt::Hybrid
