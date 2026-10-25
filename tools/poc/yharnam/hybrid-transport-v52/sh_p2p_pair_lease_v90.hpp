// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V90: one-use, two-account coordinated SHG2 grant on original Qt shadNet.
// Strictly in-process DEV-only test lease. This does NOT open a new listener,
// deliver an Internet credential, authenticate UDP, or arm Direct gameplay.
#include "sh_p2p_reciprocal_pair_v88.hpp"
#include "sh_pair_ready_v91.hpp"
#include <QByteArray>
#include <functional>
#include <optional>
#include <cstdint>

namespace SeamlessHunt::Hybrid {
class P2PPairLeaseV90 final {
public:
    using Resolver=std::function<std::optional<P2PLocalOfferScope>(
        const QByteArray&,const QByteArray&)>;
    P2PPairLeaseV90()=default;
    ~P2PPairLeaseV90(){Clear();}
    P2PPairLeaseV90(const P2PPairLeaseV90&)=delete;
    P2PPairLeaseV90& operator=(const P2PPairLeaseV90&)=delete;

    bool Begin(const QByteArray& account_a,const QByteArray& account_b,
               Resolver authoritative,std::uint64_t now_ms) {
        Clear();
        if(!authoritative || account_a.isEmpty() || account_b.isEmpty() ||
           account_a==account_b || !now_ms)return false;
        const auto first=authoritative(account_a,account_b);
        const auto second=authoritative(account_b,account_a);
        if(!first || !second)return false;
        P2PReciprocalOffersV88 pair{};
        if(!P2PReciprocalPairIssuerV88::Prepare(
            *first,*second,now_ms,pair.for_a,pair.for_b))
            return false;
        // Re-read AFTER preparing before retaining anything; server world
        // can change between reads if the resolver is reentrant.
        const auto confirm_a=authoritative(account_a,account_b);
        const auto confirm_b=authoritative(account_b,account_a);
        if(!confirm_a || !confirm_b ||
           !Same(*first,*confirm_a) || !Same(*second,*confirm_b)) {
            ErasePair(pair);
            return false;
        }
        if(!ready_gate_.Prepare(pair.for_a,pair.for_b,now_ms)) {
            ErasePair(pair);return false;
        }
        a_=account_a;b_=account_b;
        first_=*first;second_=*second;
        pair_=pair;
        ErasePair(pair); // no second plaintext master copy on stack
        resolver_=std::move(authoritative);
        active_=true;
        return true;
    }
    // Call ONLY after TLS cert PIN+original live epoch checks on SAME mTLS
    // 1.3 session and the V80 Begin key exchange have succeeded.
    // Failure revokes BOTH halves, never hands an orphaned master to client.
    bool Take(const QByteArray& authenticated_recipient,
              quint64 recipient_current_epoch,
              std::uint64_t now_ms,SecurePeerOfferV84& out) {
        out={};
        if(!active_ || !resolver_ || !now_ms ||
           now_ms< pair_.for_a.issued_ms ||
           now_ms>=pair_.for_a.expires_ms ||
           (issued_a_ && issued_b_)) {
            Clear();return false;
        }
        const bool a=authenticated_recipient==a_;
        const bool b=authenticated_recipient==b_;
        if((!a && !b) || (a && issued_a_) || (b && issued_b_) ||
           !recipient_current_epoch) {
            Clear();return false;
        }
        // Both directions, not just the recipient, MUST remain mutually
        // consenting in the original authenticated server's exact world.
        const auto current_a=resolver_(a_,b_);
        const auto current_b=resolver_(b_,a_);
        if(!current_a || !current_b ||
           !Same(first_,*current_a) || !Same(second_,*current_b)) {
            Clear();return false;
        }
        const auto& offer=a?pair_.for_a:pair_.for_b;
        if(offer.session_epoch!=recipient_current_epoch ||
           !SecureOfferV84Detail::Valid(offer,now_ms)) {
            Clear();return false;
        }
        out=offer;
        if(a)issued_a_=true;else issued_b_=true;
        // After both halves were issued, retain only separate HMAC READY
        // commitments, authoritative resolver and epochs. Immediately wipe
        // master so it is not available while awaiting both TLS receipts.
        if(issued_a_ && issued_b_) {
            ErasePair(pair_);pair_={};active_=false;
        }
        return true;
    }
    // Only from a certificate-pinned CURRENT mTLS session already issued
    // this exact paired SHG2 offer. Never call from plaintext SHLK or UDP.
    bool MarkReady(const QByteArray& authenticated_recipient,
                   quint64 current_epoch,
                   std::span<const std::uint8_t> proof,
                   std::uint64_t now_ms,bool& both_ready) {
        both_ready=false;
        // First client may report READY before the other client has
        // even asked for its offer. Only the reporting side needs to
        // have received its own SHG2 ticket at this point.
        const bool reporting_a=authenticated_recipient==a_;
        const bool reporting_b=authenticated_recipient==b_;
        if((!reporting_a && !reporting_b) ||
           (reporting_a && !issued_a_) ||
           (reporting_b && !issued_b_) ||
           !resolver_ || !ready_gate_.PairBinding() || !now_ms) {
            Clear();return false;
        }
        const auto cur_a=resolver_(a_,b_);
        const auto cur_b=resolver_(b_,a_);
        if(!cur_a || !cur_b || !Same(first_,*cur_a) ||
           !Same(second_,*cur_b)) {
            Clear();return false;
        }
        const auto digest=P2PFullIdentityIssuerV84::AccountDigest(
            authenticated_recipient);
        if(!digest) {Clear();return false;}
        const auto accepted=ready_gate_.Mark(
            *digest,current_epoch,first_.world_revision,true,proof,now_ms);
        if(accepted==PairReadyGateV91::Result::Denied){
            Clear();return false;
        }
        both_ready=accepted==PairReadyGateV91::Result::BothReady;
        return true;
    }
    bool BothReady(std::uint64_t now_ms) const noexcept {
        return ready_gate_.BothReady(now_ms);
    }
    bool Active() const noexcept{return active_;}
    void Clear() noexcept {
        ready_gate_.Clear();
        ErasePair(pair_);
        pair_={};
        if(!a_.isEmpty())std::fill(a_.begin(),a_.end(),char(0));
        if(!b_.isEmpty())std::fill(b_.begin(),b_.end(),char(0));
        a_.clear();b_.clear();
        first_={};second_={};
        resolver_={};active_=false;issued_a_=false;issued_b_=false;
    }
private:
    static bool Same(const P2PLocalOfferScope& x,
                     const P2PLocalOfferScope& y) noexcept {
        return x.recipient==y.recipient && x.peer==y.peer &&
            x.recipient_epoch==y.recipient_epoch &&
            x.peer_epoch==y.peer_epoch &&
            x.world_revision==y.world_revision &&
            x.physical_ipv4_host==y.physical_ipv4_host &&
            x.physical_port_host==y.physical_port_host &&
            x.virtual_ipv4_host==y.virtual_ipv4_host &&
            x.virtual_port_host==y.virtual_port_host;
    }
    static void ErasePair(P2PReciprocalOffersV88& v) noexcept {
        CryptoDetail::Erase(v.for_a.direction_key);
        CryptoDetail::Erase(v.for_b.direction_key);
    }
    QByteArray a_{},b_{};
    P2PLocalOfferScope first_{},second_{};
    P2PReciprocalOffersV88 pair_{};
    PairReadyGateV91 ready_gate_{};
    Resolver resolver_{};
    bool active_=false,issued_a_=false,issued_b_=false;
};
} // namespace SeamlessHunt::Hybrid
