// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "native_direct_filter.hpp"
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using namespace SeamlessHunt::Direct;
static void u16(std::vector<std::uint8_t>& b,std::uint16_t n){b.push_back(n&255);b.push_back(n>>8);}
static void u32(std::vector<std::uint8_t>& b,std::uint32_t n){for(int i=0;i<32;i+=8)b.push_back(n>>i&255);}
static std::vector<std::uint8_t> game(std::vector<std::uint32_t> channels){
  std::vector<std::uint8_t> b{0xff,0xff,0xff,0xff,'S','H','A','D',0x40,1,1,'X'};
  u32(b,1);u32(b,1);u32(b,0);u16(b,static_cast<std::uint16_t>(channels.size()));
  for(auto channel:channels){b.push_back(0);u32(b,5);u32(b,8);u32(b,channel);u32(b,0);}
  return b;
}
int main(){
  for(std::uint32_t channel=0;channel<68;++channel)
    assert(DirectSafeGameFrame(game({channel}))==IsStaticallyDirectSafe(channel));
  assert(DirectSafeGameFrame(game({1,2,3})));
  assert(!DirectSafeGameFrame(game({1,0x14,3})));
  assert(!DirectSafeGameFrame(game({0x2c})));
  assert(!DirectSafeGameFrame(game({0x27})));
  assert(!DirectSafeGameFrame(game({68})));
  assert(!DirectSafeGameFrame(game({})));
  auto malformed=game({1});malformed.pop_back();
  assert(!DirectSafeGameFrame(malformed));
  malformed=game({1});malformed[8]=0x41;assert(!DirectSafeGameFrame(malformed));
  malformed=game({1});malformed[9]=5;assert(!DirectSafeGameFrame(malformed));
  malformed=game({1});malformed[10]=250;assert(!DirectSafeGameFrame(malformed));
  malformed=game({1});malformed.push_back(0);assert(!DirectSafeGameFrame(malformed));
  malformed=game({1});malformed[26]=9;assert(!DirectSafeGameFrame(malformed));
  std::cout<<"PASS: 68 native channels, filtered/mixed/empty/malformed frames cannot bypass shadNet\n";
}
