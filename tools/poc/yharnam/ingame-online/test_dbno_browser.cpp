// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "session_matchmaking.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::InGame;
static Party P(std::string group,std::string player){return {group,{{player,60}}};}
static Room R(std::string id,bool dbno,bool invasions,Scaling scaling=Scaling::PartyBalanced) {
    Room r;r.id=id;r.title=id;r.game_build="YT-pinned";r.region="eu";
    r.rules.dbno_enabled=dbno;r.rules.invasions_enabled=invasions;
    r.rules.invasion_slots=2;r.rules.scaling=scaling;
    r.defenders.push_back(P("host-"+id,"hostplayer-"+id));
    return r;
}
int main(){
    const auto now=Matchmaker::Clock::now();
    Matchmaker mm;
    assert(mm.Create(R("on",true,true,Scaling::Challenging)));
    assert(mm.Create(R("off",false,false)));
    auto visitor=P("visitor","hunter1");
    assert(mm.Browse(visitor,Mode::Coop,"YT-pinned",now).size()==2);
    RoomFilters f;f.dbno=true;f.invasions=true;f.scaling=Scaling::Challenging;
    const auto filtered=mm.Browse(visitor,Mode::Coop,"YT-pinned",now,f);
    assert(filtered.size()==1&&filtered[0].id=="on"&&filtered[0].dbno_enabled);
    assert(mm.QuickPlay(visitor,Mode::Coop,"YT-pinned",now,f)==std::optional<std::string>{"on"});
    f.dbno=false;
    assert(mm.Browse(visitor,Mode::Coop,"YT-pinned",now,f).empty());
    f={};f.dbno=false;f.invasions=false;
    assert(mm.QuickPlay(visitor,Mode::Coop,"YT-pinned",now,f)==std::optional<std::string>{"off"});
    auto room=mm.Snapshot("on");
    assert(room&&room->rules_revision==1);
    auto rules=room->rules;rules.dbno_enabled=false;
    assert(!mm.Configure("on","hunter1",rules,1));
    assert(!mm.Configure("on","hostplayer-on",rules,77));
    assert(mm.Configure("on","hostplayer-on",rules,1));
    assert(mm.Snapshot("on")->rules_revision==2);
    assert(!mm.Configure("on","hostplayer-on",rules,1));
    assert(mm.StartHunt("on","hostplayer-on"));
    assert(!mm.Configure("on","hostplayer-on",room->rules,3));
    auto secret=R("secret",true,true);secret.rules.password_protected=true;
    assert(mm.Create(secret));
    assert(CanJoin(secret,visitor,Mode::Invasion,"YT-pinned",true).reject==Reject::Private);
    assert(mm.Browse(visitor,Mode::Coop,"YT-pinned",now).size()==1);
    auto full=R("full",true,true);full.rules.total_slots=2;
    assert(mm.Create(full));
    auto ticket=mm.Reserve("full",P("last","lastguest"),Mode::Coop,"YT-pinned",false,now);
    assert(ticket&&mm.Confirm(ticket->id,now));
    RoomFilters show;show.hide_full=false;show.min_free_slots=0;
    auto cards=mm.Browse(visitor,Mode::Coop,"YT-pinned",now,show);
    bool seen=false;
    for(const auto& card:cards)if(card.id=="full"){
        seen=true;assert(!card.joinable&&card.free_slots==0&&card.reason==Reject::Full);
    }
    assert(seen);
    assert(mm.QuickPlay(visitor,Mode::Coop,"YT-pinned",now,show)!=std::optional<std::string>{"full"});
    std::cout<<"PASS: DBNO public filtering, host-only settings, Quick Play, full/secret protection\n";
}
