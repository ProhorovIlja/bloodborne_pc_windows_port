// SPDX-License-Identifier: GPL-2.0-or-later
// Seamless Hunt: offline-tested matchmaking rules; NOT the live shadNet or in-game UI yet.
#pragma once
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <map>
#include <mutex>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
namespace SeamlessHunt::InGame {
enum class Mode { Coop, Invasion };
enum class Visibility { Public, Private };
enum class Scaling { Vanilla, PartyBalanced, Challenging };
enum class RoutePreference { DirectP2P, RelayOnly };
enum class Reject { None, Closed, Private, InvasionsDisabled, InvasionCap, Full, InvalidGroup, MismatchedBuild, LevelMismatch, DuplicatePlayer };
struct Hunter { std::string id; int level=4; };
struct Party { std::string id; std::vector<Hunter> members; };
struct Rules {
    Visibility visibility=Visibility::Public;
    Scaling scaling=Scaling::PartyBalanced;
    RoutePreference route=RoutePreference::DirectP2P;
    bool invasions_enabled=false;
    unsigned total_slots=4; // hard-capped to 4 until 5 slots verified in native gameplay
    unsigned invasion_slots=0;
    int level_tolerance=40;
};
struct Room {
    std::string id, game_build;
    Rules rules;
    std::vector<Party> defenders, invaders;
    bool open=true;
};
struct Admission {
    Reject reject=Reject::None;
    unsigned free_slots=0;
    explicit operator bool() const { return reject==Reject::None; }
};
inline unsigned Count(const std::vector<Party>& ps) {
    unsigned n=0;
    for(const auto& p:ps) n+=static_cast<unsigned>(p.members.size());
    return n;
}
inline unsigned Players(const Room& r) { return Count(r.defenders)+Count(r.invaders); }
inline bool UniqueMembers(const Party& p) {
    if(p.id.empty() || p.members.empty()) return false;
    std::set<std::string> ids;
    for(const auto& h:p.members)
        if(h.id.empty() || h.level<4 || h.level>544 || !ids.insert(h.id).second) return false;
    return true;
}
inline Admission CanJoin(const Room& r, const Party& group, Mode mode,
    std::string_view build, bool server_authorized_private, unsigned reserved=0,
    unsigned reserved_invaders=0, bool five_slot_runtime_certified=false) {
    if(!r.open) return {Reject::Closed};
    if(!UniqueMembers(group) || r.defenders.empty() || !UniqueMembers(r.defenders.front())) return {Reject::InvalidGroup};
    if(build!=r.game_build || build.empty()) return {Reject::MismatchedBuild};
    if(r.rules.visibility==Visibility::Private && !server_authorized_private) return {Reject::Private};
    for(const auto& side:{&r.defenders,&r.invaders})
        for(const auto& p:*side) {
            if(p.id==group.id) return {Reject::DuplicatePlayer};
            for(const auto& h:group.members) for(const auto& existing:p.members)
                if(h.id==existing.id) return {Reject::DuplicatePlayer};
        }
    if(mode==Mode::Invasion && !r.rules.invasions_enabled) return {Reject::InvasionsDisabled};
    if(mode==Mode::Invasion && Count(r.invaders)+reserved_invaders+group.members.size()>r.rules.invasion_slots)
        return {Reject::InvasionCap};
    const unsigned cap=std::min(r.rules.total_slots, five_slot_runtime_certified ? 5u : 4u);
    if(Players(r)+reserved+group.members.size()>cap) return {Reject::Full};
    const int host_level=r.defenders.front().members.front().level;
    if(std::any_of(group.members.begin(),group.members.end(),[&](const Hunter& h){
        return std::abs(h.level-host_level)>r.rules.level_tolerance;
    })) return {Reject::LevelMismatch};
    return {Reject::None,cap-Players(r)-reserved-static_cast<unsigned>(group.members.size())};
}
// Atomic reservation/commit for team-vs-team matchmaking. Authenticate the caller at the HTTP/API boundary.
class Matchmaker {
public:
    using Clock=std::chrono::steady_clock;
    using Time=Clock::time_point;
    struct Ticket { std::string id,room_id; Mode mode; Party party; Time until; };
    explicit Matchmaker(bool five_slot_runtime_certified=false):certified_(five_slot_runtime_certified){}
    bool Create(Room r) {
        if(r.id.empty() || r.game_build.empty() || r.defenders.size()!=1 ||
           !UniqueMembers(r.defenders.front()) || !r.invaders.empty() ||
           r.rules.total_slots<Players(r) || r.rules.total_slots>(certified_?5u:4u) ||
           r.rules.invasion_slots>r.rules.total_slots || r.rules.level_tolerance<0 || r.rules.level_tolerance>544) return false;
        std::scoped_lock lock(mu_);
        return rooms_.emplace(r.id,std::move(r)).second;
    }
    std::optional<std::string> QuickPlay(const Party& p,Mode m,std::string_view build,Time now) {
        std::scoped_lock lock(mu_);
        Expire(now);
        for(const auto& [id,r]:rooms_) {
            if(r.rules.visibility!=Visibility::Public) continue;
            const auto [n,inv]=Reserved(id);
            if(CanJoin(r,p,m,build,false,n,inv,certified_)) return id;
        }
        return std::nullopt;
    }
    std::optional<Ticket> Reserve(std::string room_id,Party party,Mode mode,std::string_view build,
        bool server_authorized_private,Time now,std::chrono::seconds ttl=std::chrono::seconds{20}) {
        std::scoped_lock lock(mu_);
        Expire(now);
        if(ttl<=std::chrono::seconds{0} || ttl>std::chrono::seconds{60}) return std::nullopt;
        const auto room=rooms_.find(room_id);
        if(room==rooms_.end()) return std::nullopt;
        for(const auto& [id,t]:tickets_) for(const auto& h:party.members) for(const auto& other:t.party.members)
            if(h.id==other.id) return std::nullopt;
        const auto [n,inv]=Reserved(room_id);
        if(!CanJoin(room->second,party,mode,build,server_authorized_private,n,inv,certified_))
            return std::nullopt;
        Ticket t{std::to_string(++next_id_),std::move(room_id),mode,std::move(party),now+ttl};
        tickets_.emplace(t.id,t);
        return t;
    }
    bool Confirm(std::string_view ticket_id,Time now) {
        std::scoped_lock lock(mu_);
        Expire(now);
        const auto it=tickets_.find(std::string(ticket_id));
        if(it==tickets_.end()) return false;
        const auto room=rooms_.find(it->second.room_id);
        if(room==rooms_.end() || !room->second.open) { tickets_.erase(it); return false; }
        if(it->second.mode==Mode::Invasion) room->second.invaders.push_back(it->second.party);
        else room->second.defenders.push_back(it->second.party);
        tickets_.erase(it);
        return true;
    }
    bool Close(std::string_view room_id) {
        std::scoped_lock lock(mu_);
        const auto r=rooms_.find(std::string(room_id));
        if(r==rooms_.end()) return false;
        r->second.open=false;
        for(auto t=tickets_.begin();t!=tickets_.end();)
            if(t->second.room_id==room_id)t=tickets_.erase(t);else ++t;
        return true;
    }
    std::optional<Room> Snapshot(std::string_view room_id)const{
        std::scoped_lock lock(mu_);
        const auto it=rooms_.find(std::string(room_id));
        return it==rooms_.end()?std::nullopt:std::optional<Room>{it->second};
    }
private:
    std::pair<unsigned,unsigned> Reserved(const std::string& room)const{
        unsigned n=0,inv=0;
        for(const auto& [id,t]:tickets_)if(t.room_id==room){
            const auto add=static_cast<unsigned>(t.party.members.size());
            n+=add;if(t.mode==Mode::Invasion)inv+=add;
        }
        return {n,inv};
    }
    void Expire(Time now){
        for(auto it=tickets_.begin();it!=tickets_.end();)
            if(now>=it->second.until)it=tickets_.erase(it);else ++it;
    }
    bool certified_=false;
    mutable std::mutex mu_;
    std::map<std::string,Room> rooms_;
    std::map<std::string,Ticket> tickets_;
    std::uint64_t next_id_=0;
};
} // namespace SeamlessHunt::InGame
