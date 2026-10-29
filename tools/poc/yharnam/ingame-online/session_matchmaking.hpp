// SPDX-License-Identifier: GPL-2.0-or-later
// Seamless Hunt: offline-tested matchmaking rules; NOT the live shadNet or in-game UI yet.
#pragma once
#include <algorithm>
#include <chrono>
#include <cctype>
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
enum class Reject { None, Closed, Private, InvasionsDisabled, InvasionCap, Full, InvalidGroup, MismatchedBuild, LevelMismatch, DuplicatePlayer, Blocked };
struct Hunter { std::string id; int level=4; std::string public_name; };
struct Party { std::string id; std::vector<Hunter> members; };
struct Rules {
    Visibility visibility=Visibility::Public;
    Scaling scaling=Scaling::PartyBalanced;
    RoutePreference route=RoutePreference::DirectP2P;
    bool invasions_enabled=false;
    // Down But Not Out: lobby-authoritative, host controlled (default preserves YT behavior).
    bool dbno_enabled=true;
    // A passworded room is always immune to random invasions and Quick Play.
    bool password_protected=false;
    unsigned total_slots=4; // hard-capped to 4 until 5 slots verified in native gameplay
    unsigned invasion_slots=0;
    int level_tolerance=40;
};
struct Room {
    std::string id, game_build;
    std::string title, region="any";
    Rules rules;
    std::vector<Party> defenders, invaders;
    // Server-owned host blacklist: auth principal IDs, not spoofable display names.
    std::set<std::string> blocked_account_ids;
    bool open=true;
    bool started=false;
    std::uint64_t rules_revision=1;
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
    if((r.rules.visibility==Visibility::Private || r.rules.password_protected) &&
       !server_authorized_private) return {Reject::Private};
    // Invading a password-protected/private room is forbidden even with a valid invitation.
    if(mode==Mode::Invasion && (r.rules.visibility==Visibility::Private || r.rules.password_protected))
        return {Reject::Private};
    for(const auto& side:{&r.defenders,&r.invaders})
        for(const auto& p:*side) {
            if(p.id==group.id) return {Reject::DuplicatePlayer};
            for(const auto& h:group.members) for(const auto& existing:p.members)
                if(h.id==existing.id) return {Reject::DuplicatePlayer};
        }
    for(const auto& hunter:group.members)
        if(r.blocked_account_ids.contains(hunter.id)) return {Reject::Blocked};
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
// The same filter structure is consumed by the in-game browser and Quick Play.
// Optional booleans: nullopt = Any, false = Off, true = On.
// A passworded/private room NEVER appears in public search.
struct RoomFilters {
    std::optional<bool> dbno, invasions;
    std::optional<Scaling> scaling;
    std::optional<RoutePreference> route;
    std::string region="any";
    std::string host_name_query, title_query; // public names only; not account IDs
    unsigned min_free_slots=1;
    bool hide_full=true;
    bool include_started=false;
};
struct RoomView {
    std::string id,title,region;
    unsigned players=0, reserved=0, max_players=0, free_slots=0;
    bool dbno_enabled=false, invasions_enabled=false, started=false, joinable=false;
    Scaling scaling=Scaling::PartyBalanced;
    RoutePreference route=RoutePreference::DirectP2P;
    std::uint64_t rules_revision=0;
    Reject reason=Reject::None;
    std::string host_name;
    std::vector<std::string> public_members; // explicit public_name only
};
struct RoomPage {
    std::vector<RoomView> rooms;
    std::size_t next_offset=0;
    bool has_more=false;
};
// ASCII-insensitive only; production UI must use Unicode case folding.
inline bool ContainsAsciiFolded(std::string_view source,std::string_view fragment) {
    if(fragment.empty())return true;
    const auto eq=[](unsigned char a,unsigned char b) {
        return std::tolower(a)==std::tolower(b);
    };
    return std::search(source.begin(),source.end(),fragment.begin(),fragment.end(),eq)!=source.end();
}
inline bool MatchesFilters(const Room& r, const RoomFilters& f) {
    if(!r.open || r.rules.visibility!=Visibility::Public || r.rules.password_protected)return false;
    if(r.started && !f.include_started)return false;
    if(!ContainsAsciiFolded(r.title,f.title_query))return false;
    const auto& host=r.defenders.front().members.front();
    if(!ContainsAsciiFolded(host.public_name,f.host_name_query))return false;
    if(f.dbno && r.rules.dbno_enabled!=*f.dbno)return false;
    if(f.invasions && r.rules.invasions_enabled!=*f.invasions)return false;
    if(f.scaling && r.rules.scaling!=*f.scaling)return false;
    if(f.route && r.rules.route!=*f.route)return false;
    if(!f.region.empty() && f.region!="any" && r.region!="any" && r.region!=f.region)return false;
    return true;
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
    std::optional<std::string> QuickPlay(const Party& p,Mode m,std::string_view build,Time now,
        const RoomFilters& filters={}) {
        std::scoped_lock lock(mu_);
        Expire(now);
        for(const auto& [id,r]:rooms_) {
            if(!MatchesFilters(r,filters)) continue;
            const auto [n,inv]=Reserved(id);
            const unsigned free=r.rules.total_slots>Players(r)+n ? r.rules.total_slots-Players(r)-n:0;
            if(free<filters.min_free_slots || (filters.hide_full&&free==0))continue;
            if(CanJoin(r,p,m,build,false,n,inv,certified_)) return id;
        }
        return std::nullopt;
    }
    // Public browser, using exactly the same privacy and mechanics filters as Quick Play.
    std::vector<RoomView> Browse(const Party& p,Mode m,std::string_view build,Time now,
                                 const RoomFilters& filters={}) {
        std::scoped_lock lock(mu_);
        Expire(now);
        std::vector<RoomView> out;
        for(const auto& [id,r]:rooms_) {
            if(!MatchesFilters(r,filters) || r.game_build!=build)continue;
            const auto [reserved,inv]=Reserved(id);
            const unsigned cap=std::min(r.rules.total_slots,certified_?5u:4u);
            const unsigned free=Players(r)+reserved>=cap?0:cap-Players(r)-reserved;
            if((filters.hide_full&&free==0) || free<filters.min_free_slots)continue;
            const Admission admit=CanJoin(r,p,m,build,false,reserved,inv,certified_);
            // When 'show full' is selected, display a disabled room, not an invalid match.
            if(admit.reject==Reject::Blocked)continue; // never expose a blacklisted host's lobby
            if(!admit && !(admit.reject==Reject::Full&&!filters.hide_full))continue;
            out.push_back(RoomView{id,r.title,r.region,Players(r),reserved,cap,free,
                r.rules.dbno_enabled,r.rules.invasions_enabled,r.started,
                static_cast<bool>(admit),r.rules.scaling,r.rules.route,r.rules_revision,
                admit.reject});
            out.back().host_name=r.defenders.front().members.front().public_name;
            for(const auto* side:{&r.defenders,&r.invaders})
                for(const auto& squad:*side)
                    for(const auto& member:squad.members)
                        if(!member.public_name.empty())out.back().public_members.push_back(member.public_name);
        }
        std::stable_sort(out.begin(),out.end(),[](const RoomView& a,const RoomView& b) {
            if(a.joinable!=b.joinable)return a.joinable>b.joinable;
            if(a.players!=b.players)return a.players>b.players;
            return a.id<b.id;
        });
        return out;
    }
    // Wire-safe bounded results: never broadcast a global full directory to all players.
    // An HTTP handler must still rate-limit and bind query to its authenticated principal.
    RoomPage BrowsePage(const Party& viewer,Mode mode,std::string_view build,Time now,
                        const RoomFilters& filters={},std::size_t offset=0,
                        std::size_t page_size=25) {
        auto all=Browse(viewer,mode,build,now,filters);
        const std::size_t cap=std::clamp(page_size,std::size_t{1},std::size_t{50});
        RoomPage page;
        if(offset>=all.size())return page;
        const auto end=offset+std::min(cap,all.size()-offset);
        page.rooms.assign(all.begin()+offset,all.begin()+end);
        page.next_offset=end;
        page.has_more=end<all.size();
        return page;
    }
    // Caller identity MUST come from authenticated shadNet session, never arbitrary request text.
    // Block applies to future admissions/tickets. Live kick + route/token revocation
    // must be implemented at the authoritative game server before production.
    bool SetBlocked(std::string_view room_id,std::string_view authenticated_host,
                    std::string_view target_id,bool blocked) {
        std::scoped_lock lock(mu_);
        auto it=rooms_.find(std::string(room_id));
        if(it==rooms_.end()||it->second.defenders.empty()||
           it->second.defenders.front().members.empty())return false;
        Room& room=it->second;
        const auto& host=room.defenders.front().members.front().id;
        if(authenticated_host!=host||target_id.empty()||target_id==host)return false;
        if(blocked) {
            if(!room.blocked_account_ids.contains(std::string(target_id)) &&
               room.blocked_account_ids.size()>=512)return false;
            room.blocked_account_ids.insert(std::string(target_id));
            for(auto ticket=tickets_.begin();ticket!=tickets_.end();) {
                if(ticket->second.room_id==room.id &&
                   std::any_of(ticket->second.party.members.begin(),ticket->second.party.members.end(),
                    [&](const Hunter& h){return h.id==target_id;}))
                    ticket=tickets_.erase(ticket);
                else ++ticket;
            }
        } else {
            room.blocked_account_ids.erase(std::string(target_id));
        }
        ++room.rules_revision;
        return true;
    }
    // Only a server-authenticated room host may call this. Never accept a claimed
    // host_id directly from an unauthenticated HTTP request.
    bool Configure(const std::string& room_id,const std::string& authenticated_host,
                   const Rules& next,std::uint64_t expected_revision) {
        std::scoped_lock lock(mu_);
        auto it=rooms_.find(room_id);
        if(it==rooms_.end() || it->second.started || it->second.defenders.empty() ||
           it->second.defenders.front().members.empty() ||
           authenticated_host!=it->second.defenders.front().members.front().id ||
           expected_revision!=it->second.rules_revision)return false;
        if(next.total_slots<Players(it->second) || next.total_slots>(certified_?5u:4u) ||
           next.invasion_slots>next.total_slots || next.level_tolerance<0 ||
           next.level_tolerance>544)return false;
        it->second.rules=next;
        ++it->second.rules_revision;
        // Pending Quick Play tickets were admitted under old rules; invalidate them.
        for(auto ticket=tickets_.begin();ticket!=tickets_.end();) {
            if(ticket->second.room_id==room_id)ticket=tickets_.erase(ticket);
            else ++ticket;
        }
        return true;
    }
    bool StartHunt(const std::string& room_id,const std::string& authenticated_host) {
        std::scoped_lock lock(mu_);
        auto it=rooms_.find(room_id);
        if(it==rooms_.end()||it->second.defenders.empty()||
           it->second.defenders.front().members.empty()||
           authenticated_host!=it->second.defenders.front().members.front().id||it->second.started)return false;
        it->second.started=true;
        ++it->second.rules_revision;
        return true;
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
