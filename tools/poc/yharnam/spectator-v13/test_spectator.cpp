#ifdef NDEBUG
#undef NDEBUG
#endif
#include "spectator_policy.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::Spectate;
int main(){
  State s;std::vector<Hunter> team{
    {"A",Life::Up,true,true,{1,2,3}},
    {"B",Life::Down,true,true,{2,2,3}},
    {"C",Life::Up,true,true,{9,4,4}},
    {"D",Life::Up,false,true,{8,2,1}}
  };
  s.Update(Life::Up,team);assert(s.mode==Mode::Inactive&&s.selected==-1);
  s.Update(Life::Down,team);assert(s.mode==Mode::Follow&&s.selected==0);
  s.Cycle(+1,team);assert(s.selected==2);
  s.Cycle(+1,team);assert(s.selected==0);
  s.Cycle(-1,team);assert(s.selected==2);
  s.Free();assert(s.mode==Mode::Free);s.Cycle(1,team);assert(s.selected==2);
  s.Free();assert(s.mode==Mode::Follow);
  team[2].life=Life::Dead;s.Update(Life::Down,team);assert(s.selected==0);
  team[0].has_position=false;s.Update(Life::Down,team);
  assert(s.selected==-1&&s.mode==Mode::Inactive);
  s.Free();assert(s.mode==Mode::Free);
  s.Update(Life::Up,team);assert(s.mode==Mode::Inactive&&s.selected==-1);
  team[0].has_position=true;team[0].position[0]=NAN;
  s.Update(Life::Down,team);assert(s.selected==-1);
  team[0].position[0]=10;s.Update(Life::Down,team);
  assert(s.mode==Mode::Follow&&s.selected==0);
  s.Update(Life::Off,team);assert(s.mode==Mode::Inactive);
  std::cout<<"PASS V13: down/dead transitions, same-map targets, cycling, freecam\n";
}
