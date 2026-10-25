// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V90: one-use, two-account coordinated SHG2 grant on original Qt shadNet.
// Strictly in-process DEV-only test lease. This does NOT open a new listener,
// deliver an Internet credential, authenticate UDP, or arm Direct gameplay.
#include "sh_p2p_reciprocal_pair_v88.hpp"
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
        a_=account_a;b_=account_b;
        first_=*first;second_=*second;
        pair_=pair;
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
        // Copy already left in out. Once BOTH halves were consumed there
        // is no legitimate server-side reason to retain the pair master.
        // Clear also makes the next TLS OFFER fail closed immediately.
        if(issued_a_ && issued_b_)Clear();
        return true;
    }
    bool Active() const noexcept{return active_;}
    void Clear() noexcept {
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
    Resolver resolver_{};
    bool active_=false,issued_a_=false,issued_b_=false;
};
} // namespace SeamlessHunt::Hybrid
