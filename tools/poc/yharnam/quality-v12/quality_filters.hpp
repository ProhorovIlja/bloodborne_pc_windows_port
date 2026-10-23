// SPDX-License-Identifier: GPL-2.0-or-later
// Client-side candidate discovery, NOT server authorization.
#pragma once
#include <algorithm>
#include <cstdint>
#include <optional>
#include <string>
#include <utility>
#include <vector>
namespace SeamlessHunt::Quality {
enum class Tri : std::uint8_t { Any, Off, On };
enum class Preset : std::uint8_t { Balanced, LowLatency, Friends, Unrestricted };
enum class Link : std::uint8_t { Unknown, Direct, Relay };
enum class Sort : std::uint8_t { BestPing, MostPlayers, MostFree };
struct Peer {
    std::string id;
    std::optional<unsigned> measured_rtt_ms;
    Link measured_link=Link::Unknown;
    bool authenticated=false;
    std::int64_t observed_at_ms=0;
};
struct Room {
    std::string id, game_build, region, host_member;
    unsigned occupied=0, capacity=0, reserved=0;
    bool public_room=true, password_protected=false, dbno_enabled=true,
         invasions_enabled=false, session_started=false, host_invasions_opt_in=false;
    std::vector<Peer> peers;
};
struct Filter {
    std::string game_build, region;
    Tri dbno=Tri::Any, invasions=Tri::Any;
    std::optional<unsigned> maximum_ping_ms;
    unsigned needed_slots=1;
    bool hide_full=true, include_started=true, require_direct=false;
    bool permit_unmeasured=true;
    bool allow_cross_region=true;
    Sort sort=Sort::BestPing;
};
struct Match {
    bool eligible=false, measured=false;
    unsigned worst_rtt_ms=0;
    Link route=Link::Unknown;
    unsigned free_slots=0;
};
inline bool Is(Tri rule,bool value){return rule==Tri::Any||(rule==Tri::On)==value;}
inline Match Evaluate(const Room& r,const Filter& f,std::int64_t now_ms){
    Match out;
    if(r.capacity<r.occupied || r.reserved>r.capacity-r.occupied)return out;
    out.free_slots=r.capacity-r.occupied-r.reserved;
    if(!r.public_room||r.password_protected||r.game_build!=f.game_build||
       !Is(f.dbno,r.dbno_enabled)||!Is(f.invasions,r.invasions_enabled)||
       (f.invasions==Tri::On&&!r.host_invasions_opt_in)||
       (!f.include_started&&r.session_started)||
       (!f.allow_cross_region&&!f.region.empty()&&r.region!=f.region)||
       (f.hide_full&&out.free_slots==0)||out.free_slots<f.needed_slots)return out;
    bool any_valid=false,all_valid=true,all_direct=true;
    for(const auto& peer:r.peers){
        const bool fresh=peer.authenticated && peer.measured_rtt_ms &&
            *peer.measured_rtt_ms>0 && *peer.measured_rtt_ms<=5000 &&
            now_ms>=peer.observed_at_ms && now_ms-peer.observed_at_ms<=15000 &&
            (peer.measured_link==Link::Direct||peer.measured_link==Link::Relay);
        if(!fresh){all_valid=false;all_direct=false;continue;}
        any_valid=true;
        if(peer.measured_link!=Link::Direct)all_direct=false;
        out.worst_rtt_ms=std::max(out.worst_rtt_ms,*peer.measured_rtt_ms);
    }
    out.measured=any_valid&&all_valid;
    out.route=out.measured?(all_direct?Link::Direct:Link::Relay):Link::Unknown;
    if(f.require_direct&&(!out.measured||out.route!=Link::Direct))return out;
    if(f.maximum_ping_ms&&(!out.measured||out.worst_rtt_ms>*f.maximum_ping_ms))return out;
    if(!out.measured&&!f.permit_unmeasured)return out;
    out.eligible=true;
    return out;
}
inline Filter Make(Preset p,std::string build){
    Filter f;f.game_build=std::move(build);
    switch(p){
    case Preset::LowLatency:f.maximum_ping_ms=60;f.permit_unmeasured=false;break;
    case Preset::Friends:f.include_started=true;f.permit_unmeasured=true;break;
    case Preset::Unrestricted:f.include_started=true;f.permit_unmeasured=true;break;
    default:f.maximum_ping_ms=120;f.permit_unmeasured=false;break;
    }
    return f;
}
struct Ranked {std::size_t index=0;Match match;};
inline std::vector<Ranked> Discover(const std::vector<Room>& rooms,const Filter& f,std::int64_t now_ms){
    std::vector<Ranked> result;
    for(std::size_t i=0;i<rooms.size();++i){
        auto decision=Evaluate(rooms[i],f,now_ms);
        if(decision.eligible)result.push_back({i,decision});
    }
    std::stable_sort(result.begin(),result.end(),[&](const Ranked& a,const Ranked& b){
        if(f.sort==Sort::MostPlayers&&rooms[a.index].occupied!=rooms[b.index].occupied)
            return rooms[a.index].occupied>rooms[b.index].occupied;
        if(f.sort==Sort::MostFree&&a.match.free_slots!=b.match.free_slots)
            return a.match.free_slots>b.match.free_slots;
        if(a.match.measured!=b.match.measured)return a.match.measured;
        if(a.match.measured&&a.match.worst_rtt_ms!=b.match.worst_rtt_ms)
            return a.match.worst_rtt_ms<b.match.worst_rtt_ms;
        return rooms[a.index].id<rooms[b.index].id;
    });
    return result;
}
} // namespace SeamlessHunt::Quality
