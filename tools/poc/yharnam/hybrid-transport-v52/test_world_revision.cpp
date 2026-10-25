// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_world_revision.hpp"
#include <cassert>
#include <string>
using namespace SeamlessHunt::Hybrid;
int main(){
    WorldRevisionInput base{722,0,4,101,101,"host",true,true,false,false};
    const auto first=BoundWorldRevision(base);
    assert(first!=0);
    assert(BoundWorldRevision(base)==first);
    auto second=base;
    second.world_epoch++;assert(BoundWorldRevision(second)!=first);
    second=base;
    second.map_reset_version++;assert(BoundWorldRevision(second)!=first);
    second=base;
    second.session_run++;assert(BoundWorldRevision(second)!=first);
    second=base;
    second.from_map=102;second.to_map=102;
    assert(BoundWorldRevision(second)!=first);
    second=base;
    second.current_enemy_owner="guest";
    assert(BoundWorldRevision(second)!=first);
    second=base;second.current_enemy_owner="";
    assert(BoundWorldRevision(second)!=first);
    second=base;second.current_enemy_owner=std::string(255,'a');
    assert(BoundWorldRevision(second)!=first);
    second.current_enemy_owner=std::string(256,'a');
    assert(BoundWorldRevision(second)==0);
    second=base;second.from_map=102;
    assert(BoundWorldRevision(second)==0);
    second=base;second.to_map=0;
    assert(BoundWorldRevision(second)==0);
    second=base;second.world_epoch=0;
    assert(BoundWorldRevision(second)==0);
    second=base;second.from_on_team=false;
    assert(BoundWorldRevision(second)==0);
    second=base;second.to_on_team=false;
    assert(BoundWorldRevision(second)==0);
    second=base;second.from_cut_from_team=true;
    assert(BoundWorldRevision(second)==0);
    second=base;second.to_cut_from_team=true;
    assert(BoundWorldRevision(second)==0);
    return 0;
}
