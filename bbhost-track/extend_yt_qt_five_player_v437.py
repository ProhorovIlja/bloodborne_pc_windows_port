#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Source-pinned original Qt Hub 5-link encrypted GameFrame integration.

V437 extends V435+V436 only in temporary CI overlay, never touches
production or original YT checkout. It exercises real Noise-NK links
and source-authenticated SHLK4 data, not game clients or direct P2P.
"""
from __future__ import annotations
import argparse
from pathlib import Path

ANCHOR="} // namespace\n\nint main() {"
MAIN="       V436OriginalEncryptedGameRelay() != 0) {"
ADDED=r'''
// V437: five original YT links with source-authenticated online IDs.
// Same-party 5-player coop, 4+1 and 3+2 visitor variants, map mismatch,
// impossible invader->invader traffic, spoofed sender and NAT port move.
// Endpoint authentication and GameFrame codec are original server logic;
// all five "game clients" are fake Net instances, not launched Bloodborne.
int V437FivePartyEncryptedRouteAndRebind() {
  using BloodborneCoop::PacketClass;
  using BloodborneCoop::EnemyPart;
  using BloodborneCoop::PacketEnds;

  Net net;
  const Endpoint Maria{0x7F000001u, 40004u};
  const Endpoint Gehrman{0x7F000001u, 40005u};
  const std::vector<std::pair<Endpoint, const char*>> people={
      {Kaniel,"Kaniel"},{Ada,"Ada"},{Eileen,"Eileen"},
      {Maria,"Maria"},{Gehrman,"Gehrman"}};
  std::map<quint64, QString> team, visiting;
  std::map<quint64, u32> maps;
  for(const auto& person:people) {
    team[person.first.Key()]="yarnham-team";
    maps[person.first.Key()]=101u;
  }
  net->SetPartyOf([&](const Endpoint& ep)->QString {
    const auto it=team.find(ep.Key());
    return it==team.end()?QString{}:it->second;
  });
  net->SetVisiting([&](const Endpoint& ep)->QString {
    const auto it=visiting.find(ep.Key());
    return it==visiting.end()?QString{}:it->second;
  });
  // Exact canonical original channel/map/hostile policy. No custom
  // blanket pass of all game packets, even in synthetic five-link test.
  net->SetPacketRoutes([&](const Endpoint& from,const Endpoint& to,u32 channel) {
    const auto from_team=team.find(from.Key());
    const auto to_team=team.find(to.Key());
    const auto fm=maps.find(from.Key());
    const auto tm=maps.find(to.Key());
    if(from_team==team.end()||to_team==team.end() ||
       fm==maps.end()||tm==maps.end())return false;
    const PacketEnds ends{fm->second,tm->second,EnemyPart::None,EnemyPart::None};
    const bool hostile=from_team->second!=to_team->second;
    const bool from_visitor=visiting.find(from.Key())!=visiting.end();
    return hostile ? BloodborneCoop::RoutesHostilePacket(channel,ends,from_visitor)
                   : BloodborneCoop::RoutesNativePacket(channel,ends);
  });
  for(std::size_t i=0;i<people.size();++i) {
    auto linked=net.Receive(
        people[i].first,HelloFrom(people[i].second),static_cast<qint64>(i));
    const auto welcome=SentTo(linked,people[i].first);
    CHECK(welcome.size()==1);
    const auto ack=DecodeWelcome(welcome[0]);
    CHECK(ack && ack->accepted);
  }
  CHECK(net->Members()==5 && net.unopened==0);

  const auto transmit=[&](const Endpoint& from,const char* signed_id,
                          const char* destination,u32 channel,qint64 ms) {
    BloodborneCoop::GameFrame f{signed_id,7,0,0,{}};
    f.entries={{PacketClass::Unreliable,static_cast<u32>(ms),PacketOn(channel)}};
    return net.Receive(from,Encode(Data{
       VirtualEndpointOf(destination),GamePacketsFrame(f)}),ms);
  };
  // In original GameLink a denied unreliable native entry disappears,
  // but the authenticated ACK-only GameFrame is deliberately forwarded.
  // Confusing an empty ACK with zero datagrams causes false failures.
  const auto only_ack=[&](const Hub::Result& routed,const Endpoint& target) {
    const auto sent=SentTo(routed,target);
    if(sent.size()!=1)return false;
    const auto data=DecodeData(sent[0]);
    if(!data || data->frame.size()<9)return false;
    const auto frame=BloodborneCoop::DecodeGameFrame({
        reinterpret_cast<const u8*>(data->frame.constData())+9,
        static_cast<std::size_t>(data->frame.size()-9)});
    return frame && frame->entries.empty();
  };

  // 5/5 cooperative hunters send encrypted game data by original
  // virtual YT addresses, never each other's physical UDP address.
  for(std::size_t i=1;i<people.size();++i) {
    const auto routed=transmit(Kaniel,"Kaniel",people[i].second,0x06u,20+i);
    const auto ciphertext=SentTo(routed,people[i].first);
    CHECK(ciphertext.size()==1 && routed.sends.size()==1);
    const auto data=DecodeData(ciphertext[0]);
    CHECK(data && data->peer==VirtualEndpointOf("Kaniel"));
    const auto original=BloodborneCoop::DecodeGameFrame({
        reinterpret_cast<const u8*>(data->frame.constData())+9,
        static_cast<std::size_t>(data->frame.size()-9)});
    CHECK(original && original->sender=="Kaniel" && original->instance==7 &&
          original->entries.size()==1 &&
          original->entries[0].packet==PacketOn(0x06u));
  }
  for(std::size_t i=1;i<people.size();++i) {
    CHECK(SentTo(transmit(people[i].first,people[i].second,"Kaniel",0x06u,
                          30+i),Kaniel).size()==1);
  }
  CHECK(SentTo(transmit(Ada,"Ada","Eileen",0x06u,40),Eileen).size()==1);
  CHECK(transmit(Kaniel,"Eileen","Ada",0x06u,41).sends.isEmpty());

  // Change to four cooperating plus one invading visitor. A visitor
  // only receives the original game's allowed hostile-channel packets.
  team[Gehrman.Key()]="visitor-1";
  visiting[Gehrman.Key()]="yarnham-team";
  CHECK(SentTo(transmit(Kaniel,"Kaniel","Gehrman",0x06u,50),Gehrman).size()==1);
  CHECK(SentTo(transmit(Gehrman,"Gehrman","Kaniel",0x06u,51),Kaniel).size()==1);
  CHECK(only_ack(transmit(Kaniel,"Kaniel","Gehrman",0x31u,52),Gehrman));
  const auto forbidden_control=Encode(Data{VirtualEndpointOf("Gehrman"),
      QByteArray::fromHex("ffffffff")+"SHAD"+char(0x41)+"world"});
  CHECK(net.Receive(Kaniel,forbidden_control,53).sends.isEmpty());

  // Three cooperators and two independent visitors: hostile guests are
  // allowed to visit host, but are NOT in a team with each other.
  team[Maria.Key()]="visitor-2";
  visiting[Maria.Key()]="yarnham-team";
  CHECK(SentTo(transmit(Maria,"Maria","Kaniel",0x06u,60),Kaniel).size()==1);
  CHECK(SentTo(transmit(Gehrman,"Gehrman","Kaniel",0x06u,61),Kaniel).size()==1);
  CHECK(SentTo(transmit(Kaniel,"Kaniel","Maria",0x06u,62),Maria).size()==1);
  CHECK(transmit(Maria,"Maria","Gehrman",0x06u,63).sends.isEmpty());

  // Map mismatch blocks same-map movement even on an otherwise linked,
  // authenticated host-invader path. The YT original policy is oracle.
  maps[Maria.Key()]=202u;
  CHECK(only_ack(transmit(Kaniel,"Kaniel","Maria",0x06u,64),Maria));
  maps[Maria.Key()]=101u;

  // Original YT virtual endpoint survives NAT port rebind. Old source
  // link becomes invalid; new signed-in link must be used for delivery.
  const Endpoint ada_moved{0x7F000001u,40099u};
  const auto linked=net.Receive(ada_moved,HelloFrom("Ada"),70);
  CHECK(net->Members()==5 &&
        net->VirtualOf(ada_moved)==VirtualEndpointOf("Ada") &&
        !net->VirtualOf(Ada));
  CHECK(linked.gone.size()==1 && linked.gone[0]==Ada);
  team[ada_moved.Key()]=team.at(Ada.Key());
  maps[ada_moved.Key()]=maps.at(Ada.Key());
  team.erase(Ada.Key());
  maps.erase(Ada.Key());
  const auto rebound=transmit(Kaniel,"Kaniel","Ada",0x06u,71);
  CHECK(SentTo(rebound,ada_moved).size()==1 &&
        SentTo(rebound,Ada).isEmpty());
  CHECK(transmit(Ada,"Ada","Kaniel",0x06u,72).sends.isEmpty());
  CHECK(SentTo(transmit(ada_moved,"Ada","Kaniel",0x06u,73),
               Kaniel).size()==1);
  CHECK(net.unopened==0);
  std::cout<<"V437 YT ORIGINAL NOISE-NK FIVE HUNTER ROUTE REBIND PASS\n";
  return 0;
}
'''
def patch(path:Path)->None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>230000:
        raise ValueError("missing/oversized original YT Qt test overlay")
    original=path.read_text(encoding="utf-8")
    if original.count(ANCHOR)!=1 or original.count(MAIN)!=1 or \
       original.count("V436OriginalEncryptedGameRelay()")!=2:
        raise ValueError("V436 Qt integration anchor drift")
    updated=original.replace(ANCHOR,ADDED+"\n"+ANCHOR).replace(
       MAIN,"       V436OriginalEncryptedGameRelay() != 0 ||\n"
            "       V437FivePartyEncryptedRouteAndRebind() != 0) {")
    if updated.count("V437FivePartyEncryptedRouteAndRebind()")!=2:
        raise ValueError("V437 injection not unique")
    path.write_text(updated,encoding="utf-8")
    print("SHYT_V437_ORIGINAL_YT_NOISE_NK_FIVE_HUNTER_FIXTURE_ADDED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--overlay-test",type=Path,required=True)
    a=p.parse_args()
    try:patch(a.overlay_test)
    except (ValueError,OSError,UnicodeError) as exc:
        raise SystemExit("SHYT_V437_FIVE_HUNTER_FIXTURE_REFUSED: "+
                         type(exc).__name__) from None
