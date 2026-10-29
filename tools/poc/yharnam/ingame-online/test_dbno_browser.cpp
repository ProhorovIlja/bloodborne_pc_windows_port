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
    // Existing public browser now supports searching consented display names and titles.
    // Authenticated account IDs must never appear as public name fallbacks.
    auto social=R("social",true,true);
    social.title="Night Hunt";
    social.defenders.front().members.front().public_name="Lady Maria";
    auto companion=P("companion","ally-private-account");
    companion.members.front().public_name="The Wanderer";
    social.defenders.push_back(companion);
    assert(mm.Create(social));
    RoomFilters query;
    query.host_name_query="mArIa";
    query.title_query="NIGHT";
    auto matches=mm.Browse(visitor,Mode::Coop,"YT-pinned",now,query);
    assert(matches.size()==1 && matches.front().id=="social");
    assert(matches.front().host_name=="Lady Maria");
    assert(matches.front().public_members.size()==2);
    assert(matches.front().public_members[1]=="The Wanderer");
    assert(matches.front().host_name!="hostplayer-social");
    assert(mm.QuickPlay(visitor,Mode::Coop,"YT-pinned",now,query)==
           std::optional<std::string>{"social"});
    query.host_name_query="not Maria";
    assert(mm.Browse(visitor,Mode::Coop,"YT-pinned",now,query).empty());
    query.host_name_query="Maria";

    // A pending admission ticket must be revoked when the real host blocks the account.
    auto pending=mm.Reserve("social",visitor,Mode::Coop,"YT-pinned",false,now);
    assert(pending);
    assert(!mm.SetBlocked("social","hunter1","hunter1",true));
    assert(!mm.SetBlocked("social","hunter1","hostplayer-social",true));
    assert(!mm.SetBlocked("social","hostplayer-social","hostplayer-social",true));
    assert(mm.SetBlocked("social","hostplayer-social","hunter1",true));
    assert(!mm.Confirm(pending->id,now));
    assert(CanJoin(*mm.Snapshot("social"),visitor,Mode::Coop,"YT-pinned",false).reject==
           Reject::Blocked);
    assert(mm.Browse(visitor,Mode::Coop,"YT-pinned",now,query).empty());
    assert(!mm.QuickPlay(visitor,Mode::Coop,"YT-pinned",now,query));
    assert(!mm.Reserve("social",visitor,Mode::Invasion,"YT-pinned",false,now));
    // A different account is not blocked by public display name matching.
    assert(mm.Browse(P("other-group","another-hunter"),Mode::Coop,"YT-pinned",now,query).size()==1);
    assert(mm.SetBlocked("social","hostplayer-social","hunter1",false));
    assert(mm.Browse(visitor,Mode::Coop,"YT-pinned",now,query).size()==1);

    // The directory is explicitly paged, even with hundreds of sessions.
    auto first=mm.BrowsePage(visitor,Mode::Coop,"YT-pinned",now,{},0,1);
    assert(first.rooms.size()==1 && first.has_more && first.next_offset==1);
    auto second=mm.BrowsePage(visitor,Mode::Coop,"YT-pinned",now,{},first.next_offset,1);
    assert(second.rooms.size()==1 && first.rooms[0].id!=second.rooms[0].id);
    auto exhausted=mm.BrowsePage(visitor,Mode::Coop,"YT-pinned",now,{},9999,9999);
    assert(exhausted.rooms.empty() && !exhausted.has_more);
    for(int i=0;i<60;++i)assert(mm.Create(R("bulk-"+std::to_string(i),true,false)));
    auto bounded=mm.BrowsePage(visitor,Mode::Coop,"YT-pinned",now,{},0,100000);
    assert(bounded.rooms.size()==50 && bounded.has_more && bounded.next_offset==50);
    std::cout<<"PASS: browser filters, public host/roster, capped pages, server-host blocklist\n";
    std::cout<<"PASS: DBNO public filtering, host-only settings, Quick Play, full/secret protection\n";
}
