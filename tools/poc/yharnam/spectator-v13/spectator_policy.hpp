// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>
namespace SeamlessHunt::Spectate {
enum class Mode : std::uint8_t { Inactive=0, Follow=1, Free=2 };
enum class Life : std::uint8_t { Off=0, Up=1, Down=2, Dead=3 };
struct Hunter {
  std::string name;
  Life life=Life::Off;
  bool same_map=false,has_position=false;
  std::array<float,3> position{};
};
inline bool Valid(const Hunter& h){
  return h.life==Life::Up&&h.same_map&&h.has_position&&
    std::all_of(h.position.begin(),h.position.end(),[](float f){
      return std::isfinite(f)&&std::abs(f)<100000;
    });
}
struct State {
  Mode mode=Mode::Inactive;
  int selected=-1;
  Life own=Life::Up;
  void Update(Life life,const std::vector<Hunter>& hunters){
    own=life;
    if(life!=Life::Down&&life!=Life::Dead){mode=Mode::Inactive;selected=-1;return;}
    if(mode==Mode::Inactive)mode=Mode::Follow;
    if(selected>=0&&selected<static_cast<int>(hunters.size())&&Valid(hunters[selected]))return;
    selected=-1;
    for(std::size_t i=0;i<hunters.size();++i)if(Valid(hunters[i])){
      selected=static_cast<int>(i);break;
    }
    if(selected<0&&mode==Mode::Follow)mode=Mode::Inactive;
  }
  void Follow(const std::vector<Hunter>& hunters){
    if(own!=Life::Down&&own!=Life::Dead)return;
    mode=Mode::Follow;
    if(selected<0)Update(own,hunters);
    if(selected<0)mode=Mode::Inactive;
  }
  void Free(){
    if(own==Life::Down||own==Life::Dead)
      mode=mode==Mode::Free?Mode::Follow:Mode::Free;
  }
  void Cycle(int delta,const std::vector<Hunter>& hunters){
    if(mode!=Mode::Follow||hunters.empty())return;
    const int count=static_cast<int>(hunters.size());
    for(int i=1;i<=count;++i){
      int next=(selected+delta*i)%count;if(next<0)next+=count;
      if(Valid(hunters[next])){selected=next;return;}
    }
  }
};
} // namespace SeamlessHunt::Spectate
