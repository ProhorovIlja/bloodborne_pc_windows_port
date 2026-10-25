// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_hunter_presence_v95.hpp"
#include <cassert>
#include <string>
using namespace SeamlessHunt::HunterPresenceV95;
static Hunter H(int level,int str,int skl,int blt,int arc,
                int vit=30,int end=20) {
    return {level,{vit,end,str,skl,blt,arc}};
}
int main() {
    const Hunter cane=H(120,10,50,7,18,50,30);
    assert(Valid(cane));
    assert(Build(cane)=="Skill/Arcane");
    assert(Details(cane)=="BL 120 | Skill/Arcane");
    assert(Build(H(100,50,50,9,6))=="Quality");
    assert(Build(H(60,50,12,8,7))=="Strength");
    assert(Build(H(65,8,30,32,7))=="Skill/Bloodtinge");
    assert(Build(H(90,55,12,6,30))=="Strength/Arcane");
    assert(Build(H(120,25,30,23,7))=="Hybrid");
    assert(Build(H(12,12,12,8,7,30,20))=="Developing Hunter");
    assert(Build(H(12,17,17,17,17,30,20))=="Developing Hunter");
    assert(Build(H(12,18,17,17,17,30,20))=="Strength");
    assert(Build(H(12,17,17,18,17,30,20))=="Bloodtinge");
    assert(Build(H(12,17,17,17,18,30,20))=="Arcane");
    // Constitution/stamina >=18 NEVER masquerade as a STR/ARC build.
    assert(Build(H(50,8,10,7,6,50,50))=="Developing Hunter");
    assert(Details(cane,{true,false})=="BL 120");
    assert(Details(cane,{false,true})=="Skill/Arcane");
    assert(Details(cane,{false,false}).empty());
    // Corrupt/no save should never publish nonsense in Discord.
    for(int level:{-1,0,545,1000}){
        Hunter bad=cane;bad.blood_level=level;
        assert(!Valid(bad));assert(Build(bad).empty());
        assert(Details(bad).empty());
    }
    for(int badStat:{-1,0,100,999}){
        Hunter bad=cane;bad.stats[3]=badStat;
        assert(!Valid(bad));assert(Build(bad).empty());
    }
    // No network ids, player name, region, session, IP, or invitation
    // secret exists in this local pure model.
    return 0;
}
