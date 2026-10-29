// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V103: original game's bounded, per-peer SHG2 inbox owner.
// Host + 4 co-op guests => each hunter needs up to four independent
// authenticated peer offers. Never gives a grant to an untrusted UDP frame.
// Only verified TLS1.3 V102 OFFER/READY may reach InstallVerified.
// This stage does NOT Arm Direct RX/TX, send probes or migrate game ACKs.
#include "sh_native_grant_inbox_v84.hpp"
#include <array>
#include <cstddef>
#include <cstdint>

namespace SeamlessHunt::Hybrid {
class NativeTeamGrantSlotsV103 final {
public:
    static constexpr std::size_t kMaxPeers=4;
    NativeTeamGrantSlotsV103()=default;
    ~NativeTeamGrantSlotsV103(){RevokeAll();}
    NativeTeamGrantSlotsV103(const NativeTeamGrantSlotsV103&)=delete;
    NativeTeamGrantSlotsV103& operator=(const NativeTeamGrantSlotsV103&)=delete;

    // Call under the original game's native_grant_mutex. Never hold the
    // mutex across network/TLS I/O. Worker owns the verified inbox until
    // this short transfer and remains responsible for its own secrets.
    bool InstallVerified(NativeSealedGrantInboxV84& worker,
                         std::uint64_t pair_id,
                         std::uint64_t current_link_generation,
                         std::uint64_t now_ms) noexcept {
        if(!pair_id || !current_link_generation || !now_ms)return false;
        Sweep(now_ms);
        // Do not replace an independent live pair or accept a duplicate.
        for(auto& slot:slots_)
            if(slot.pair_id==pair_id)return false;
        const auto* grant=worker.PendingForNat(now_ms);
        if(!grant || grant->pair_binding!=pair_id)return false;
        for(auto& slot:slots_) {
            if(slot.pair_id)continue;
            if(!worker.TransferVerifiedTo(slot.inbox,now_ms))
                return false;
            slot.pair_id=pair_id;
            slot.link_generation=current_link_generation;
            return true;
        }
        return false; // a fifth peer is never silently admitted
    }

    // Trusted game-owned read only admission for the *selected* peer.
    // A failed identity/epoch/world/consent refresh drops only its slot.
    // Never infer route readiness from the presence of this secret.
    const SecurePeerOfferV84* PendingForNat(
        std::uint64_t pair_id,std::uint64_t current_link_generation,
        std::uint64_t now_ms) noexcept {
        if(!pair_id || !current_link_generation || !now_ms)return nullptr;
        for(auto& slot:slots_) {
            if(slot.pair_id!=pair_id)continue;
            if(slot.link_generation!=current_link_generation)return nullptr;
            const auto* grant=slot.inbox.PendingForNat(now_ms);
            if(!grant || grant->pair_binding!=pair_id) {
                slot.Reset();return nullptr;
            }
            return grant;
        }
        return nullptr;
    }

    bool RevokePair(std::uint64_t pair_id) noexcept {
        if(!pair_id)return false;
        for(auto& slot:slots_)
            if(slot.pair_id==pair_id) {
                slot.Reset();return true;
            }
        return false;
    }
    void Sweep(std::uint64_t now_ms) noexcept {
        for(auto& slot:slots_)
            if(slot.pair_id && !slot.inbox.PendingForNat(now_ms))
                slot.Reset();
    }
    void RevokeAll() noexcept {
        for(auto& slot:slots_)slot.Reset();
    }
    std::size_t Count() const noexcept {
        std::size_t n=0;
        for(const auto& slot:slots_)if(slot.pair_id)++n;
        return n;
    }
private:
    struct Slot {
        std::uint64_t pair_id=0;
        std::uint64_t link_generation=0;
        NativeSealedGrantInboxV84 inbox{};
        void Reset() noexcept {
            inbox.Revoke();
            pair_id=0;
            link_generation=0;
        }
    };
    std::array<Slot,kMaxPeers> slots_{};
};
} // namespace SeamlessHunt::Hybrid
