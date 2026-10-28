// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V102: team mesh, independent 64-bit server-issued SHG2 pair generations.
// This controls short-lived KEYS ONLY, never forwards game data or enables
// P2P gameplay. Server must select all pairs from its original world/consent.
#include "sh_p2p_pair_lease_v90.hpp"
#include <QByteArray>
#include <QHash>
#include <QSet>
#include <QVector>
#include <cstddef>
#include <algorithm>
#include <cstdint>
#include <limits>
#include <memory>
#include <set>
#include <vector>
#include <utility>

namespace SeamlessHunt::Hybrid {
class P2PTeamPairRegistryV102 final {
public:
    using Resolver=P2PPairLeaseV90::Resolver;
    static constexpr std::size_t kMaxPairs=512;
    static constexpr std::size_t kMaxPeersPerAccount=16;
    static constexpr std::uint64_t kLeaseMs=10000;
    P2PTeamPairRegistryV102()=default;
    ~P2PTeamPairRegistryV102(){ClearAll();}
    P2PTeamPairRegistryV102(const P2PTeamPairRegistryV102&)=delete;
    P2PTeamPairRegistryV102& operator=(const P2PTeamPairRegistryV102&)=delete;

    // Server stage only. Selector is cryptographically random, unguessable
    // in practice, and scoped to a pair of current authenticated players.
    // Selecting it DOES NOT grant authority: each call checks member + epoch
    // + both reciprocal world snapshots in P2PPairLeaseV90.
    bool Begin(const QByteArray& first,const QByteArray& second,
               Resolver authoritative,std::uint64_t now_ms,
               std::uint64_t& pair_id) {
        pair_id=0;
        if(!now_ms || now_ms>std::numeric_limits<std::uint64_t>::max()-kLeaseMs ||
           first.isEmpty() || second.isEmpty() || first==second ||
           first.size()>64 || second.size()>64 || !authoritative)return false;
        Sweep(now_ms);
        if(Count()>=kMaxPairs ||
           by_member_.value(first).size()>=static_cast<qsizetype>(kMaxPeersPerAccount) ||
           by_member_.value(second).size()>=static_cast<qsizetype>(kMaxPeersPerAccount))
            return false;
        for(const auto id:by_member_.value(first)) {
            const auto entry=by_pair_.value(id);
            if(entry && ((entry->a==first && entry->b==second) ||
                         (entry->a==second && entry->b==first)))
                return false; // no concurrent generation for SAME pair
        }
        auto entry=std::make_shared<Entry>(first,second,now_ms);
        if(!entry->lease.Begin(first,second,std::move(authoritative),now_ms))
            return false;
        const auto id=entry->lease.PairBinding();
        if(!id || by_pair_.contains(id)) {
            entry->lease.Clear();
            return false; // CSPRNG collision must not replace a pair
        }
        entry->id=id;
        by_pair_.insert(id,entry);
        by_member_[first].insert(id);
        by_member_[second].insert(id);
        pair_id=id;
        return true;
    }
    QVector<std::uint64_t> AvailableFor(const QByteArray& member,
                                        std::uint64_t now_ms) const {
        QVector<std::uint64_t> result;
        if(member.isEmpty())return result;
        for(const auto id:by_member_.value(member)) {
            const auto entry=by_pair_.value(id);
            if(entry && TimeValid(*entry,now_ms) &&
               entry->lease.HasOutstanding(now_ms) &&
               entry->lease.StillAuthorized())
                result.append(id);
        }
        std::sort(result.begin(),result.end()); // stable LIST response
        return result;
    }
    bool Take(const QByteArray& member,std::uint64_t id,quint64 current_epoch,
              std::uint64_t now_ms,SecurePeerOfferV84& out) {
        out={};
        auto entry=GetAuthorized(member,id);
        if(!entry)return false; // unrelated TLS account cannot revoke
        if(!TimeValid(*entry,now_ms) ||
           !entry->lease.Take(member,current_epoch,now_ms,out)) {
            RevokePair(id);
            return false;
        }
        return true;
    }
    bool MarkReady(const QByteArray& member,std::uint64_t id,
                   quint64 current_epoch,std::span<const std::uint8_t> proof,
                   std::uint64_t now_ms,bool& both_ready) {
        both_ready=false;
        auto entry=GetAuthorized(member,id);
        if(!entry)return false;
        if(!TimeValid(*entry,now_ms) ||
           !entry->lease.MarkReady(member,current_epoch,proof,
                                   now_ms,both_ready)) {
            RevokePair(id);
            return false;
        }
        return true;
    }
    bool BothReady(const QByteArray& member,std::uint64_t id,
                   std::uint64_t now_ms) const {
        const auto entry=GetAuthorized(member,id);
        return entry && TimeValid(*entry,now_ms) &&
               entry->lease.BothReady(now_ms);
    }
    bool RevokePair(std::uint64_t id) noexcept {
        const auto it=by_pair_.find(id);
        if(it==by_pair_.end())return false;
        auto entry=it.value(); // retain owner while deleting both indexes
        entry->lease.Clear();
        auto drop=[this,id](const QByteArray& who) {
            auto m=by_member_.find(who);
            if(m==by_member_.end())return;
            m.value().remove(id);
            if(m.value().isEmpty())by_member_.erase(m);
        };
        drop(entry->a);drop(entry->b);
        by_pair_.erase(it);
        return true;
    }
    // Original game-world discovery is the ONLY source of permitted pairs.
    // Drop pending mTLS grants as soon as a member leaves, opts out, loads,
    // changes owner/map/party or loses its authenticated game link.
    // This revokes SERVER pending grants, not game-client keys already issued.
    std::size_t RevokeNotIn(
        const std::vector<std::pair<QByteArray,QByteArray>>& live_pairs) {
        using Key=std::pair<QByteArray,QByteArray>;
        const auto canonical=[](QByteArray a,QByteArray b)->Key {
            if(b<a)std::swap(a,b);
            return {std::move(a),std::move(b)};
        };
        std::set<Key> permitted;
        for(const auto& [a,b]:live_pairs)
            if(!a.isEmpty() && !b.isEmpty() && a!=b)
                permitted.insert(canonical(a,b));
        QVector<std::uint64_t> outdated;
        for(auto it=by_pair_.cbegin();it!=by_pair_.cend();++it) {
            const auto& entry=*it.value();
            if(!permitted.contains(canonical(entry.a,entry.b)))
                outdated.push_back(it.key());
        }
        std::size_t revoked=0;
        for(const auto id:outdated)
            if(RevokePair(id))++revoked;
        return revoked;
    }
    std::size_t RevokeAccount(const QByteArray& member) noexcept {
        const auto ids=by_member_.value(member);
        std::size_t removed=0;
        for(const auto id:ids)
            if(RevokePair(id))++removed;
        return removed;
    }
    void Sweep(std::uint64_t now_ms) {
        QVector<std::uint64_t> expired;
        for(auto it=by_pair_.cbegin();it!=by_pair_.cend();++it) {
            const auto& e=*it.value();
            if(!TimeValid(e,now_ms) || !e.lease.HasOutstanding(now_ms) ||
               !e.lease.StillAuthorized())
                expired.append(it.key());
        }
        for(const auto id:expired)RevokePair(id);
    }
    void ClearAll() noexcept {
        for(auto it=by_pair_.begin();it!=by_pair_.end();++it)
            it.value()->lease.Clear();
        by_pair_.clear();by_member_.clear();
    }
    std::size_t Count() const noexcept {
        return static_cast<std::size_t>(by_pair_.size());
    }
private:
    struct Entry {
        Entry(QByteArray first,QByteArray second,std::uint64_t now)
            :a(std::move(first)),b(std::move(second)),
             issued(now),expires(now+kLeaseMs){}
        QByteArray a,b;
        std::uint64_t id=0,issued=0,expires=0;
        P2PPairLeaseV90 lease{};
    };
    static bool TimeValid(const Entry& e,std::uint64_t now) noexcept {
        return now>=e.issued && now<e.expires;
    }
    std::shared_ptr<Entry> GetAuthorized(const QByteArray& member,
                                         std::uint64_t id) const {
        const auto it=by_pair_.constFind(id);
        if(it==by_pair_.cend())return {};
        if(it.value()->a!=member && it.value()->b!=member)return {};
        return it.value();
    }
    QHash<std::uint64_t,std::shared_ptr<Entry>> by_pair_{};
    QHash<QByteArray,QSet<std::uint64_t>> by_member_{};
};
} // namespace SeamlessHunt::Hybrid
