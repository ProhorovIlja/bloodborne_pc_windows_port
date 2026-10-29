// SPDX-License-Identifier: GPL-2.0-or-later
// Isolated invasion/DBNO policy. The actual game server must authenticate,
// sequence and route events before invoking this model. NOT live game integration.
#pragma once
#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <string_view>

namespace SeamlessHunt::InGame {
enum class InvaderLife { Alive, Downed };
enum class InvaderEvent { Ignored, Downed, Revived, Disconnected, SideDefeated };

// Only the invader faction is counted here. There may be 2-3 invaders
// depending on occupied coop slots, but never more than three.
class InvaderDbnoSide {
public:
    explicit InvaderDbnoSide(bool dbno_enabled) : dbno_enabled_(dbno_enabled) {}
    bool Join(std::string server_account_id) {
        if(ended_ || server_account_id.empty() || members_.size()>=3 ||
           members_.contains(server_account_id) || departed_.contains(server_account_id))
            return false;
        members_.emplace(std::move(server_account_id),Entry{});
        return true;
    }
    // Server-authoritative monotonic per-member event sequences, not raw player UDP.
    InvaderEvent Down(std::string_view who,std::uint64_t event_seq) {
        auto it=members_.find(std::string(who));
        if(ended_ || it==members_.end() || !event_seq ||
           event_seq<=it->second.last_seq || it->second.life==InvaderLife::Downed)
            return InvaderEvent::Ignored;
        it->second.last_seq=event_seq;
        if(!dbno_enabled_) {
            departed_.insert(it->first);
            members_.erase(it); // without DBNO, down means leave this session
            return ResolveAfterLoss(InvaderEvent::Disconnected);
        }
        it->second.life=InvaderLife::Downed;
        return AliveCount()==0 ? DefeatAll() : InvaderEvent::Downed;
    }
    InvaderEvent Revive(std::string_view who,std::string_view by,
                        std::uint64_t event_seq) {
        if(ended_ || who==by || !event_seq)return InvaderEvent::Ignored;
        auto target=members_.find(std::string(who));
        auto helper=members_.find(std::string(by));
        if(target==members_.end() || helper==members_.end() ||
           target->second.life!=InvaderLife::Downed ||
           helper->second.life!=InvaderLife::Alive ||
           event_seq<=target->second.last_seq)return InvaderEvent::Ignored;
        // Gameplay must also verify physical proximity, revive progress,
        // world/map epoch, team identity, and that the helper is really alive.
        target->second.last_seq=event_seq;
        target->second.life=InvaderLife::Alive;
        return InvaderEvent::Revived;
    }
    InvaderEvent Disconnect(std::string_view who,std::uint64_t event_seq) {
        auto it=members_.find(std::string(who));
        if(ended_ || it==members_.end() || !event_seq ||
           event_seq<=it->second.last_seq)return InvaderEvent::Ignored;
        departed_.insert(it->first);
        members_.erase(it);
        return ResolveAfterLoss(InvaderEvent::Disconnected);
    }
    std::size_t AliveCount() const {
        std::size_t n=0;
        for(const auto& [id,entry]:members_)
            if(entry.life==InvaderLife::Alive)++n;
        return n;
    }
    std::size_t DownCount() const {
        return members_.size()-AliveCount();
    }
    std::size_t ConnectedCount() const {return members_.size();}
    bool Ended() const {return ended_;}
private:
    struct Entry {
        InvaderLife life=InvaderLife::Alive;
        std::uint64_t last_seq=0;
    };
    InvaderEvent DefeatAll() {
        for(const auto& [id,entry]:members_)departed_.insert(id);
        members_.clear();
        ended_=true;
        return InvaderEvent::SideDefeated;
    }
    InvaderEvent ResolveAfterLoss(InvaderEvent normal) {
        if(members_.empty() || AliveCount()==0)return DefeatAll();
        return normal;
    }
    bool dbno_enabled_;
    bool ended_=false;
    std::map<std::string,Entry> members_;
    std::set<std::string> departed_;
};
} // namespace SeamlessHunt::InGame
