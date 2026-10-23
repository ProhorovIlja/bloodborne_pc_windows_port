// SPDX-License-Identifier: GPL-2.0-or-later
// Yharnam Together pinned static Pass-only game channel gate.
// Based on server/coop/packet_routes.h @ 77e350743a7cb4524cfcc1782fb6e3af64e25b15
// Map/owner-dependent packets MUST still pass through shadNet.
#pragma once
#include <cstddef>
#include <cstdint>
#include <span>
namespace SeamlessHunt::Direct {
constexpr std::uint32_t kNativeChannelCount=0x44;
constexpr std::uint8_t kGamePacketType=0x40;
constexpr bool IsStaticallyDirectSafe(std::uint32_t channel){
  if(channel>=kNativeChannelCount)return false;
  switch(channel){
    case 0x04: case 0x05: case 0x06: case 0x0E: case 0x0F:
    case 0x12: case 0x14: case 0x15: case 0x16: case 0x17:
    case 0x24: case 0x25: case 0x27: case 0x29: case 0x2A:
    case 0x2B: case 0x2C: case 0x2D: case 0x2E: case 0x2F:
    case 0x30: case 0x31: case 0x34: case 0x36: case 0x37:
    case 0x3D: case 0x3E: case 0x40: case 0x41:
      return false;
    default:return true;
  }
}
inline bool TakeU32(std::span<const std::uint8_t> frame,std::size_t& pos,std::uint32_t& value){
  if(pos>frame.size()||frame.size()-pos<4)return false;
  value=std::uint32_t(frame[pos]) |
        std::uint32_t(frame[pos+1])<<8 |
        std::uint32_t(frame[pos+2])<<16 |
        std::uint32_t(frame[pos+3])<<24;
  pos+=4;return true;
}
inline bool DirectSafeGameFrame(std::span<const std::uint8_t> frame){
  constexpr std::size_t kGameHeader=9;
  if(frame.size()<kGameHeader+2+12+2||frame.size()>1100)return false;
  if(frame[4]!='S'||frame[5]!='H'||frame[6]!='A'||frame[7]!='D'||
     frame[8]!=kGamePacketType)return false;
  std::size_t pos=kGameHeader;
  const auto version=frame[pos++];
  if(version!=1)return false;
  const std::size_t sender=frame[pos++];
  if(sender==0||frame.size()-pos<sender+14)return false;
  pos+=sender;
  std::uint32_t instance=0,peer_instance=0,ack=0;
  if(!TakeU32(frame,pos,instance)||!TakeU32(frame,pos,peer_instance)||
     !TakeU32(frame,pos,ack))return false;
  if(frame.size()-pos<2)return false;
  const std::uint16_t count=std::uint16_t(frame[pos])|std::uint16_t(frame[pos+1])<<8;
  pos+=2;
  if(count==0||count>80)return false;
  for(std::uint16_t i=0;i<count;++i){
    if(frame.size()-pos<9)return false;
    const auto packet_class=frame[pos++];
    if(packet_class>1)return false;
    std::uint32_t sequence=0,packet_size=0;
    if(!TakeU32(frame,pos,sequence)||!TakeU32(frame,pos,packet_size))return false;
    if(packet_size<8||packet_size>frame.size()-pos)return false;
    std::size_t channel_at=pos;
    std::uint32_t channel=0;
    if(!TakeU32(frame,channel_at,channel)||!IsStaticallyDirectSafe(channel))return false;
    pos+=packet_size;
  }
  return pos==frame.size();
}
} // namespace SeamlessHunt::Direct
