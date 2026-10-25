// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V91: memory-only server readiness commitments for BOTH SHG2 recipients.
// Does NOT accept plaintext SHLK/HTTP/UDP readiness, connect NAT sockets,
// or authorize Direct game traffic. Only the future authenticated same-TLS
// application handler may call Mark using current original Qt game epochs.
#include "sh_pair_key_schedule_v89.hpp"
#include <array>
#include <algorithm>
#include <cstdint>
#include <span>

namespace SeamlessHunt::Hybrid {
class PairReadyProofV91 final {
public:
    using Tag=std::array<std::uint8_t,32>;
    static bool Create(const SecurePeerOfferV84& grant,
                       std::uint64_t now_ms,Tag& out) noexcept {
        out.fill(0);
        std::array<std::uint8_t,32> key{};
        if(!PairKeyScheduleV89::Derive(grant,true,
           PairKeyPurposeV89::ReadyProof,now_ms,key))return false;
        static constexpr char domain[]="YT-P2P/V91/READY";
        std::array<std::uint8_t,sizeof(domain)-1+8*3> signed_text{};
        std::size_t at=0;
        for(std::size_t i=0;i<sizeof(domain)-1;++i)
            signed_text[at++]=static_cast<std::uint8_t>(domain[i]);
        for(auto value:{grant.session_epoch,grant.issued_ms,grant.expires_ms}) {
            for(unsigned i=0;i<8;++i) {
                signed_text[at++]=static_cast<std::uint8_t>(value);
                value>>=8U;
            }
        }
        const bool ok=at==signed_text.size() &&
            CryptoDetail::Sha256Hmac(key,signed_text,out);
        CryptoDetail::Erase(key);CryptoDetail::Erase(signed_text);
        if(!ok)out.fill(0);
        return ok;
    }
};
class PairReadyGateV91 final {
public:
    enum class Result : std::uint8_t { Denied, WaitingPeer, BothReady };
    ~PairReadyGateV91(){Clear();}
    PairReadyGateV91()=default;
    PairReadyGateV91(const PairReadyGateV91&)=delete;
    PairReadyGateV91& operator=(const PairReadyGateV91&)=delete;

    bool Prepare(const SecurePeerOfferV84& a,
                 const SecurePeerOfferV84& b,
                 std::uint64_t now_ms) noexcept {
        Clear();
        if(!SecureOfferV84Detail::Valid(a,now_ms) ||
           !SecureOfferV84Detail::Valid(b,now_ms) ||
           a.sender_account!=b.recipient_account ||
           b.sender_account!=a.recipient_account ||
           a.recipient_account==b.recipient_account ||
           a.session_epoch==b.session_epoch && a.recipient_account==b.recipient_account ||
           a.pair_binding!=b.pair_binding || !a.pair_binding ||
           a.world_revision!=b.world_revision ||
           a.issued_ms!=b.issued_ms || a.expires_ms!=b.expires_ms ||
           a.direction_key!=b.direction_key ||
           !PairReadyProofV91::Create(a,now_ms,proof_a_) ||
           !PairReadyProofV91::Create(b,now_ms,proof_b_)) {
            Clear();return false;
        }
        id_a_=a.recipient_account;id_b_=b.recipient_account;
        epoch_a_=a.session_epoch;epoch_b_=b.session_epoch;
        world_=a.world_revision;pair_=a.pair_binding;
        issued_=a.issued_ms;expires_=a.expires_ms;active_=true;
        return true;
    }
    Result Mark(const AccountDigestV84& recipient,
                std::uint64_t currently_authorized_epoch,
                std::uint64_t currently_authorized_world,
                bool server_confirmed_both_consents,
                std::span<const std::uint8_t> proof,
                std::uint64_t now_ms) noexcept {
        if(!active_ || now_ms<issued_ || now_ms>=expires_ ||
           !server_confirmed_both_consents ||
           currently_authorized_world!=world_ || proof.size()!=32) {
            Clear();return Result::Denied;
        }
        const bool for_a=SecureOfferV84Detail::EqualDigest(recipient,id_a_);
        const bool for_b=SecureOfferV84Detail::EqualDigest(recipient,id_b_);
        if((!for_a && !for_b) ||
           (for_a && (marked_a_ || currently_authorized_epoch!=epoch_a_)) ||
           (for_b && (marked_b_ || currently_authorized_epoch!=epoch_b_)) ||
           !SecureOfferV84Detail::EqualDigest(
               proof,for_a?std::span<const std::uint8_t>(proof_a_):
                           std::span<const std::uint8_t>(proof_b_))) {
            Clear();return Result::Denied;
        }
        if(for_a)marked_a_=true;else marked_b_=true;
        if(marked_a_ && marked_b_) {
            // This only proves two valid responses arrived on separately
            // authenticated connections. It does NOT prove UDP reachability.
            ready_=true;
            CryptoDetail::Erase(proof_a_);
            CryptoDetail::Erase(proof_b_);
            return Result::BothReady;
        }
        return Result::WaitingPeer;
    }
    bool BothReady(std::uint64_t now_ms) const noexcept {
        return ready_ && active_ && now_ms>=issued_ && now_ms<expires_;
    }
    std::uint64_t PairBinding() const noexcept{return active_?pair_:0;}
    void Clear() noexcept {
        CryptoDetail::Erase(proof_a_);CryptoDetail::Erase(proof_b_);
        proof_a_={};proof_b_={};
        id_a_={};id_b_={};
        epoch_a_=0;epoch_b_=0;world_=0;pair_=0;
        issued_=0;expires_=0;
        marked_a_=false;marked_b_=false;active_=false;ready_=false;
    }
private:
    Tag proof_a_{},proof_b_{};
    AccountDigestV84 id_a_{},id_b_{};
    std::uint64_t epoch_a_=0,epoch_b_=0,world_=0,pair_=0;
    std::uint64_t issued_=0,expires_=0;
    bool marked_a_=false,marked_b_=false,active_=false,ready_=false;
};
} // namespace SeamlessHunt::Hybrid
