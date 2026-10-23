#ifdef NDEBUG
#undef NDEBUG
#endif
#include "quality_filters.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::Quality;
int main(){
 constexpr std::int64_t now=1000000;
 Room a;a.id="A";a.game_build="coop8";a.region="EU";a.capacity=4;a.occupied=2;
 a.peers={{"one",20,Link::Direct,true,now-1000},{"two",90,Link::Relay,true,now-1000}};
 auto balanced=Make(Preset::Balanced,"coop8");
 auto m=Evaluate(a,balanced,now);
 assert(m.eligible&&m.measured&&m.worst_rtt_ms==90&&m.route==Link::Relay);
 auto low=Make(Preset::LowLatency,"coop8");assert(!Evaluate(a,low,now).eligible);
 a.peers[1].measured_rtt_ms=30;a.peers[1].measured_link=Link::Direct;
 assert(Evaluate(a,low,now).eligible);
 low.require_direct=true;assert(Evaluate(a,low,now).eligible);
 a.peers[1].measured_link=Link::Relay;assert(!Evaluate(a,low,now).eligible);
 a.peers[1].measured_link=Link::Direct;a.peers[1].observed_at_ms=now-20000;
 assert(!Evaluate(a,low,now).eligible);
 a.peers[1].observed_at_ms=now-1000;a.peers[1].authenticated=false;
 assert(!Evaluate(a,low,now).eligible);
 a.peers[1].authenticated=true;a.peers[1].measured_rtt_ms.reset();
 assert(!Evaluate(a,low,now).eligible);
 auto any=Make(Preset::Unrestricted,"coop8");
 assert(Evaluate(a,any,now).eligible&&!Evaluate(a,any,now).measured);
 a.password_protected=true;assert(!Evaluate(a,any,now).eligible);
 a.password_protected=false;a.public_room=false;assert(!Evaluate(a,any,now).eligible);
 a.public_room=true;a.capacity=2;assert(!Evaluate(a,any,now).eligible);
 a.capacity=4;a.invasions_enabled=true;a.host_invasions_opt_in=false;
 any.invasions=Tri::On;assert(!Evaluate(a,any,now).eligible);
 a.host_invasions_opt_in=true;assert(Evaluate(a,any,now).eligible);
 a.game_build="wrong";assert(!Evaluate(a,any,now).eligible);
 a.game_build="coop8";any.allow_cross_region=false;any.region="US";
 assert(!Evaluate(a,any,now).eligible);
 any.region="EU";assert(Evaluate(a,any,now).eligible);
 Room b=a;b.id="B";b.peers={{"peer",15,Link::Direct,true,now-50}};
 Room c=a;c.id="C";c.peers={{"peer",35,Link::Direct,true,now-50}};
 auto ranked=Discover({a,b,c},any,now);
 assert(ranked.size()==3&&ranked[0].index==1&&ranked[1].index==2&&!ranked[2].match.measured);
 std::cout<<"PASS: worst verified RTT, privacy, invasions, stale/direct/unknown, ranking\n";
}
