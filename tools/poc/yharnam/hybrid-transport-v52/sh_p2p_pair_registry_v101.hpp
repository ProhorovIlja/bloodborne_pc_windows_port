// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V101: bounded, independently revocable original Qt server SHG2 pair leases.
// No public listener, client-chosen peer, gameplay forwarding or Direct Arm.
// Each active member has ONE unambiguous pair during this initial server-side
// staging phase. Multi-peer teams need explicit server-issued pair selectors
// before this restriction can be lifted.
#include "sh_p2p_pair_lease_v90.hpp"
#include <QHash>
#include <QSet>
#include <QByteArray>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <span>
#include <utility>

namespace SeamlessHunt::Hybrid {
class P2PPairRegistryV101 final {
public:
    using Resolver=P2PPairLeaseV90::Resolver;
    static constexpr std::size_t kMaxPairs=512;
    static constexpr std::uint64_t kLeaseMs=10000; // V88 SHG2 expiry
    P2PPairRegistryV101()=default;
    ~P2PPairRegistryV101(){ClearAll();}
    P2PPairRegistryV101(const P2PPairRegistryV101&)=delete;
    P2PPairRegistryV101& operator=(const P2PPairRegistryV101&)=delete;

    // From original Qt event loop only, using current signed-in game world.
    // A pair's lease performs TWO authoritative reads per direction.
    bool Begin(const QByteArray& first,const QByteArray& second,
               Resolver authoritative,std::uint64_t now_ms) {
        if(!now_ms || now_ms>UINT64_MAX-kLeaseMs ||
           first.isEmpty() || second.isEmpty() || first==second ||
           first.size()>64 || second.size()>64 ||
           !authoritative)return false;
        Sweep(now_ms);
        if(by_member_.contains(first) || by_member_.contains(second) ||
           Count()>=kMaxPairs)return false;
        auto fresh=std::make_shared<Entry>(first,second,now_ms);
        if(!fresh->lease.Begin(first,second,std::move(authoritative),now_ms))
            return false;
        by_member_.insert(first,fresh);
        by_member_.insert(second,fresh);
        return true;
    }

    // One current pinned TLS recipient gets its own sealed SHG2 half.
    // All failures revoke only the recipient's OWN pair.
    bool Take(const QByteArray& member,quint64 current_epoch,
              std::uint64_t now_ms,SecurePeerOfferV84& out) {
        out={};
        auto entry=Find(member);
        if(!entry)return false;
        if(!TimeValid(*entry,now_ms) ||
           !entry->lease.Take(member,current_epoch,now_ms,out)) {
            RevokeRecipient(member);
            return false;
        }
        return true;
    }
    bool MarkReady(const QByteArray& member,quint64 current_epoch,
                   std::span<const std::uint8_t> proof,
                   std::uint64_t now_ms,bool& both_ready) {
        both_ready=false;
        auto entry=Find(member);
        if(!entry)return false; // attacker cannot revoke unrelated pairs
        if(!TimeValid(*entry,now_ms) ||
           !entry->lease.MarkReady(
              member,current_epoch,proof,now_ms,both_ready)) {
            RevokeRecipient(member);
            return false;
        }
        return true;
    }
    bool HasOutstandingFor(const QByteArray& member,
                           std::uint64_t now_ms) const {
        const auto entry=Find(member);
        return entry && TimeValid(*entry,now_ms) &&
               entry->lease.HasOutstanding(now_ms);
    }
    bool BothReadyFor(const QByteArray& member,
                      std::uint64_t now_ms) const {
        const auto entry=Find(member);
        return entry && TimeValid(*entry,now_ms) &&
               entry->lease.BothReady(now_ms);
    }
    bool RevokeRecipient(const QByteArray& member) noexcept {
        auto entry=Find(member);
        if(!entry)return false;
        // Keep the shared Entry alive while removing its two index refs.
        entry->lease.Clear(); // zeroize pair master and READY commitments
        by_member_.remove(entry->first);
        by_member_.remove(entry->second);
        return true;
    }
    void Sweep(std::uint64_t now_ms) {
        QSet<QByteArray> stale;
        for(auto it=by_member_.cbegin();it!=by_member_.cend();++it) {
            const auto& entry=*it.value();
            if(!TimeValid(entry,now_ms) ||
               !entry.lease.HasOutstanding(now_ms))
                stale.insert(entry.first);
        }
        for(const auto& account:stale)
            RevokeRecipient(account);
    }
    void ClearAll() noexcept {
        for(auto it=by_member_.begin();it!=by_member_.end();++it)
            it.value()->lease.Clear(); // idempotent, never retains keys
        by_member_.clear();
    }
    std::size_t Count() const noexcept {
        return static_cast<std::size_t>(by_member_.size())/2;
    }
private:
    struct Entry final {
        Entry(QByteArray a,QByteArray b,std::uint64_t now)
            :first(std::move(a)),second(std::move(b)),created(now),
             expires(now+kLeaseMs) {}
        QByteArray first,second;
        std::uint64_t created=0,expires=0;
        P2PPairLeaseV90 lease{};
    };
    static bool TimeValid(const Entry& entry,
                          std::uint64_t now_ms) noexcept {
        return now_ms>=entry.created && now_ms<entry.expires;
    }
    std::shared_ptr<Entry> Find(const QByteArray& member) const {
        const auto it=by_member_.constFind(member);
        return it==by_member_.cend()?nullptr:it.value();
    }
    QHash<QByteArray,std::shared_ptr<Entry>> by_member_{};
};
} // namespace SeamlessHunt::Hybrid
