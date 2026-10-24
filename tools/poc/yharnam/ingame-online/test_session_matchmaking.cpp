// SPDX-License-Identifier: GPL-2.0-or-later
#include "session_matchmaking.hpp"
#include <atomic>
#include <cassert>
#include <iostream>
#include <thread>
#include <vector>
using namespace SeamlessHunt::InGame;
static Party PartyOf(const std::string& id,std::initializer_list<std::string> players,int lvl=75){
  Party party{id,{}}; for(const auto& player:players)party.members.push_back({player,lvl});return party;
}
static Room NewRoom(const std::string& id,std::initializer_list<std::string> defenders={"host","ally"},unsigned size=4) {
  Room r; r.id=id;r.game_build="YT-pinned";r.defenders.push_back(PartyOf("hosts",defenders));
  r.rules.total_slots=size;r.rules.invasions_enabled=true;r.rules.invasion_slots=2;return r;
}
int main(){
  const auto now=Matchmaker::Clock::now();
  Matchmaker mm;
  assert(mm.Create(NewRoom("room1")));
  assert(mm.Create(NewRoom("room2")));
  assert(mm.QuickPlay(PartyOf("joiners",{"guest"}),Mode::Coop,"YT-pinned",now)=="room1");
  auto ticket=mm.Reserve("room1",PartyOf("joiners",{"guest"}),Mode::Coop,"YT-pinned",false,now);
  assert(ticket && mm.Confirm(ticket->id,now));
  assert(mm.Snapshot("room1")->defenders.size()==2);
  assert(!mm.Reserve("room1",PartyOf("wrong",{"guest"}),Mode::Coop,"YT-pinned",false,now));
  assert(!mm.Reserve("room1",PartyOf("duo",{"red","blue"}),Mode::Invasion,"YT-pinned",false,now));
  assert(mm.Close("room1"));
  assert(!mm.Reserve("room1",PartyOf("new",{"other"}),Mode::Coop,"YT-pinned",false,now));

  Matchmaker private_mm;
  auto private_room=NewRoom("private");
  private_room.rules.visibility=Visibility::Private;
  assert(private_mm.Create(private_room));
  assert(!private_mm.QuickPlay(PartyOf("try",{"player"}),Mode::Coop,"YT-pinned",now));
  assert(!private_mm.Reserve("private",PartyOf("try",{"player"}),Mode::Coop,"YT-pinned",false,now));
  assert(private_mm.Reserve("private",PartyOf("try",{"player"}),Mode::Coop,"YT-pinned",true,now));

  Matchmaker inv;
  assert(inv.Create(NewRoom("inv")));
  auto attackers=inv.Reserve("inv",PartyOf("redteam",{"red","blue"}),Mode::Invasion,"YT-pinned",false,now);
  assert(attackers && inv.Confirm(attackers->id,now));
  assert(inv.Snapshot("inv")->defenders.size()==1 && inv.Snapshot("inv")->invaders.size()==1);
  assert(!inv.Reserve("inv",PartyOf("third",{"orange"}),Mode::Invasion,"YT-pinned",false,now));

  auto optout=NewRoom("no-invasions"); optout.rules.invasions_enabled=false;
  Matchmaker noinv;assert(noinv.Create(optout));
  assert(!noinv.Reserve("no-invasions",PartyOf("p",{"a1"}),Mode::Invasion,"YT-pinned",false,now));
  assert(!noinv.Reserve("no-invasions",PartyOf("p",{"a1"}),Mode::Coop,"wrong-build",false,now));

  Matchmaker four;
  assert(!four.Create(NewRoom("five",{"host","ally","other"},5)));
  Matchmaker five(true);
  assert(five.Create(NewRoom("five",{"host","ally","other"},5)));
  auto grp=five.Reserve("five",PartyOf("invaders",{"x","y"}),Mode::Invasion,"YT-pinned",false,now);
  assert(grp && five.Confirm(grp->id,now));
  auto world=five.Snapshot("five");
  assert(world && Count(world->defenders)==3 && Count(world->invaders)==2 && Players(*world)==5);

  Matchmaker ttl;
  assert(ttl.Create(NewRoom("ttl")));
  auto hold=ttl.Reserve("ttl",PartyOf("hold",{"x","y"}),Mode::Coop,"YT-pinned",false,now,std::chrono::seconds{1});
  assert(hold && !ttl.Reserve("ttl",PartyOf("extra",{"z"}),Mode::Coop,"YT-pinned",false,now));
  assert(!ttl.Confirm(hold->id,now+std::chrono::seconds{2}));
  assert(ttl.Reserve("ttl",PartyOf("extra",{"z"}),Mode::Coop,"YT-pinned",false,now+std::chrono::seconds{2}));

  Matchmaker race;assert(race.Create(NewRoom("race")));
  std::atomic<int> wins=0; std::vector<std::thread> jobs;
  for(int i=0;i<16;++i)jobs.emplace_back([&,i]{
    const auto suffix=std::to_string(i);
    auto t=race.Reserve("race",PartyOf("g"+suffix,{"p"+suffix}),Mode::Coop,"YT-pinned",false,now);
    if(t && race.Confirm(t->id,now))++wins;
  });
  for(auto& job:jobs)job.join();
  assert(wins==2);
  std::cout<<"PASS: Quick Play, public/private rooms, group invasions, 3v2 certification gate, TTL, concurrent slots\n";
}
