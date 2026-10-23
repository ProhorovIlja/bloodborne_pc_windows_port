// SPDX-License-Identifier: GPL-2.0-or-later
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "native_shlk_adapter.hpp"
#include <cassert>
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
  Identity aa;aa.epoch=20;aa.self_virtual={0x0a000002,3658};aa.peer_virtual={0x0a000003,3658};
  for(unsigned i=0;i<32;++i)aa.pair_secret[i]=static_cast<std::uint8_t>(i+1);
  for(unsigned i=0;i<16;++i)aa.room[i]=static_cast<std::uint8_t>(i+6);
  Identity bb=aa;std::swap(bb.self_virtual,bb.peer_virtual);
  NativeAdapter a,b;
  Endpoint phys_a{0x7f000001,60010},phys_b{0x7f000001,60011};
  assert(a.Authorize(aa,phys_b,true));assert(b.Authorize(bb,phys_a,true));
  assert(!a.TryGame(aa.peer_virtual,game({1}),900));
  for(auto& tx:a.Tick(1000)){
    auto rx=b.Receive(tx.bytes,phys_a,1001);
    for(auto& ans:rx.replies)a.Receive(ans.bytes,phys_b,1002);
  }
  for(auto& tx:b.Tick(1000)){
    auto rx=a.Receive(tx.bytes,phys_b,1001);
    for(auto& ans:rx.replies)b.Receive(ans.bytes,phys_a,1002);
  }
  auto allowed=a.TryGame(aa.peer_virtual,game({1,2}),1010);
  assert(allowed);
  auto got=b.Receive(allowed->bytes,phys_a,1011);
  assert(got.data && got.data->game_frame==game({1,2}));
  assert(!a.TryGame(aa.peer_virtual,game({0x06}),1012));
  assert(!a.TryGame(aa.peer_virtual,game({1,0x14}),1012));
  assert(!a.TryGame(aa.peer_virtual,game({0x2c}),1012));
  // A key-holding peer tries to bypass server channel policy.
  Packet forged{Type::Game,aa.room,aa.self_virtual,aa.peer_virtual,aa.epoch,1'000'000,1013,game({0x06})};
  auto rejected=b.Receive(Encode(forged,aa.pair_secret),phys_a,1014);
  assert(rejected.recognized && !rejected.data);
  a.Tick(5000);
  assert(!a.TryGame(aa.peer_virtual,game({1}),5001));
  std::cout<<"PASS: direct game frame, MAC-valid forbidden frame rejected, timeout relay fallback\n";
}
