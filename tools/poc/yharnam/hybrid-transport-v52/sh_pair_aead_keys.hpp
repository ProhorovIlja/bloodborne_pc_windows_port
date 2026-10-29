// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Direction-separated SHY2 AES-256-GCM keys and nonce salts from an existing
// server-coordinated SHG2 pair secret. This does NOT trust UDP or create a
// verified PeerTicket. Caller must use a verified, current mTLS SHG2 inbox
// AND its authoritative account, peer, team, map, world-epoch and consent.
// Not wired into the original game until both real peers prove a Direct path.
#include "sh_pair_key_schedule_v89.hpp"
#include <array>
#include <cstdint>
#include <span>
#include <string_view>

namespace SeamlessHunt::Hybrid {

struct NativePairAeadMaterial final {
    std::array<std::uint8_t,32> key{};
    std::array<std::uint8_t,4> salt{};
    NativePairAeadMaterial()=default;
    ~NativePairAeadMaterial(){Clear();}
    NativePairAeadMaterial(const NativePairAeadMaterial&)=delete;
    NativePairAeadMaterial& operator=(const NativePairAeadMaterial&)=delete;
    void Clear() noexcept {
        CryptoDetail::Erase(key);
        CryptoDetail::Erase(salt);
    }
};

class NativePairAeadKeys final {
public:
    static bool DeriveFromVerifiedInbox(
        const SecurePeerOfferV84& verified_offer,
        bool outbound,std::uint64_t now_ms,
        NativePairAeadMaterial& output) noexcept {
        output.Clear();
        // Structural Valid is an additional check, not proof of provenance.
        // Only a sealed, account-verified SHG2 inbox can call this API.
        std::array<std::uint8_t,32> directional_game_master{};
        if(!PairKeyScheduleV89::Derive(
              verified_offer,outbound,PairKeyPurposeV89::GameData,
              now_ms,directional_game_master))return false;
        static constexpr std::string_view key_context="YT-SHY2-GAME-AES256-KEY-V1";
        static constexpr std::string_view salt_context="YT-SHY2-GAME-NONCE-SALT-V1";
        const auto bytes=[](std::string_view s) noexcept {
            return std::span<const std::uint8_t>(
                reinterpret_cast<const std::uint8_t*>(s.data()),s.size());
        };
        std::array<std::uint8_t,32> salt_digest{};
        const bool ok=CryptoDetail::Sha256Hmac(
                directional_game_master,bytes(key_context),output.key) &&
            CryptoDetail::Sha256Hmac(
                directional_game_master,bytes(salt_context),salt_digest);
        if(ok)std::copy_n(salt_digest.begin(),output.salt.size(),
                          output.salt.begin());
        CryptoDetail::Erase(directional_game_master);
        CryptoDetail::Erase(salt_digest);
        if(!ok || !SecureOfferV84Detail::Nonzero(output.key) ||
           !SecureOfferV84Detail::Nonzero(output.salt)) {
            output.Clear();return false;
        }
        return true;
    }
};
} // namespace SeamlessHunt::Hybrid
