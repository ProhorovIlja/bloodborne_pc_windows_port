// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "p2p_route_policy.hpp"
#include "sh_yharnam_ui_scale.hpp"
#include "hud_layout.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace SeamlessHunt::InGame;
int main(){
    PeerRoutes routes;
    assert(routes.Decide("guest",DataChannel::GameData).route==Route::Relay);
    assert(!routes.Begin("guest",false,100,9));
    assert(routes.Begin("guest",true,100,9));
    const auto e=routes.Epoch("guest");
    assert(routes.Decide("guest",DataChannel::GameData).route==Route::Relay);
    assert(!routes.Confirm("guest",9,e,false,110));
    assert(!routes.Confirm("guest",10,e,true,110));
    assert(!routes.Confirm("guest",9,e,true,99));
    assert(routes.Confirm("guest",9,e,true,110));
    assert(routes.Decide("guest",DataChannel::GameData).route==Route::Direct);
    assert(routes.Decide("guest",DataChannel::AccountRpc).route==Route::Relay);
    assert(routes.Decide("guest",DataChannel::WorldControl).route==Route::Relay);
    assert(routes.Decide("guest",DataChannel::LobbyControl).route==Route::Relay);
    routes.PeerAuthenticatedTraffic("guest",2000);
    routes.Tick(5000);
    assert(routes.Decide("guest",DataChannel::GameData).route==Route::Relay);
    assert(!routes.Confirm("guest",9,e,true,5001));
    assert(routes.Begin("guest",true,6000,11));
    routes.Tick(9500);
    assert(routes.State("guest")==DirectState::Relay);
    assert(routes.Begin("guest",true,10000,12));
    assert(routes.Confirm("guest",12,routes.Epoch("guest"),true,10010));
    routes.SetRelayOnly(true);
    assert(routes.Decide("guest",DataChannel::GameData).route==Route::Relay);
    assert(!routes.Begin("guest",true,11000,13));
    assert(SetTeamScalePercent(115)==110);
    assert(SetTeamScalePercent(87)==85);
    const auto five=TeamCards(1920,960,150,5);
    assert(five.count==5 && five.scale>0.79f && five.scale<0.81f);
    assert(HudRows(4).scale==0.75f);
    assert(RoleRussian(HunterRole::Invader)=="ВТОРЖЕНЕЦ");
    assert(ToneFor(HunterRole::Invader)==RoleTone::Blood);
    std::cout<<"PASS: Direct/Relay transitions, epoch rejection, server-only control, five-wide UI, invader roles\n";
}
