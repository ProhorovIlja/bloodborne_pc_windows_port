// SPDX-License-Identifier: GPL-2.0-or-later
// V403: ORIGINAL YT 1.3.1 net_link.h compared with new BBHost C bridge,
// both data directions, server controls, tampered or incomplete packets.
// All dummy P2P payloads and addresses are non-live, not retail game data.
#include "shyt_yt_link_wire_v403.h"
#include "core/libraries/network/net_link.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace YT=Libraries::Net::Link;
static std::uint32_t rnd(std::uint32_t& x) {
    x^=x<<13;x^=x>>17;x^=x<<5;return x;
}
static bool same(const std::vector<u8>& native,const std::uint8_t* c,std::size_t n) {
    return native.size()==n && std::equal(native.begin(),native.end(),c);
}
int main() {
    std::uint32_t state=0xBEDA7821u;
    std::array<uint8_t,SHYT_YT_LINK_WIRE_MAX_V403> a{},b{},received{};
    std::size_t used=0,got=0;
    std::uint64_t cases=0;
    for(int t=0;t<512;++t) {
        std::vector<u8> p2p(4u+static_cast<std::size_t>(rnd(state)%1201u));
        p2p[0]=0xff;p2p[1]=0xff;p2p[2]=0xff;p2p[3]=0xff;
        for(auto &byte:p2p)
            byte=static_cast<u8>(rnd(state)>>24);
        p2p[0]=0xff;p2p[1]=0xff;p2p[2]=0xff;p2p[3]=0xff;
        // Network byte order fields remain opaque integers exactly as the
        // real YT encode/decode does on little-endian x64 systems.
        const u32 addr=rnd(state),seq=rnd(state);
        const u16 port=static_cast<u16>(rnd(state));
        const u64 sent=(static_cast<u64>(rnd(state))<<32)|rnd(state);
        const auto real=YT::EncodeData(addr,port,p2p);
        if (!shyt_yt_link_encode_data_v403(
               addr,port,p2p.data(),p2p.size(),a.data(),a.size(),&used) ||
            !same(real,a.data(),used) ||
            shyt_yt_link_kind_v403(a.data(),used)!=3)
            return 11;
        u32 read_addr=0;u16 read_port=0;
        if(!shyt_yt_link_decode_data_v403(
              a.data(),used,&read_addr,&read_port,received.data(),
              received.size(),&got) ||
           read_addr!=addr || read_port!=port ||
           got!=p2p.size() ||
           std::memcmp(received.data(),p2p.data(),got)!=0)
            return 12;
        auto decoded_by_original=YT::DecodeData({a.data(),used});
        if(!decoded_by_original ||
           decoded_by_original->addr_nbo!=addr ||
           decoded_by_original->port_nbo!=port ||
           !std::equal(decoded_by_original->frame.begin(),
                       decoded_by_original->frame.end(),p2p.begin()))
            return 13;
        // YT Data does not have a payload length field: trimming a
        // datagram can still form a smaller valid Data. Instead require
        // the complete frame to be rejected when destination is too small.
        if(shyt_yt_link_decode_data_v403(
             a.data(),used,&read_addr,&read_port,
             received.data(),p2p.size()-1,&got) || got)
            return 14;
        if(shyt_yt_link_decode_data_v403(
             a.data(),YT::DataHeaderSize+3u,&read_addr,&read_port,
             received.data(),received.size(),&got) || got)
            return 24;
        const auto native_ping=YT::Encode(YT::Kind::Ping,YT::Ping{seq,sent});
        if(!shyt_yt_link_encode_ping_v403(
              4,seq,sent,b.data(),b.size(),&got) ||
           !same(native_ping,b.data(),got))
            return 15;
        u32 check_seq=0;u64 check_ms=0;
        if(!shyt_yt_link_decode_ping_v403(
              4,b.data(),got,&check_seq,&check_ms) ||
           check_seq!=seq || check_ms!=sent)
            return 16;
        const auto coop=YT::EncodeCoop(p2p);
        std::size_t decoded_coop=0;
        if(!shyt_yt_link_encode_coop_v403(
              p2p.data(),p2p.size(),b.data(),b.size(),&got) ||
           !same(coop,b.data(),got) ||
           !shyt_yt_link_decode_coop_v403(
              b.data(),got,received.data(),received.size(),&decoded_coop) ||
           decoded_coop!=p2p.size() ||
           std::memcmp(received.data(),p2p.data(),decoded_coop)!=0)
            return 17;
        ++cases;
    }
    LinkAuth::Cookie cookie{};
    LinkAuth::Key key{};
    for(size_t i=0;i<cookie.size();++i)cookie[i]=static_cast<u8>(i+0x10);
    for(size_t i=0;i<key.size();++i)key[i]=static_cast<u8>(i+0x20);
    const auto real_cookie=YT::EncodeCookie(cookie,0,key);
    uint8_t c_cookie[16],c_pub[32],work=123;
    if(!shyt_yt_link_decode_cookie_v403(
       real_cookie.data(),real_cookie.size(),c_cookie,c_pub,&work) ||
       work!=0 || !std::equal(cookie.begin(),cookie.end(),c_cookie) ||
       !std::equal(key.begin(),key.end(),c_pub))return 18;
    const auto welcome=YT::Encode(YT::Welcome{true,"fictional-player-accepted"});
    char reason[256];int accepted=0;
    if(!shyt_yt_link_decode_welcome_v403(
       welcome.data(),welcome.size(),&accepted,reason,sizeof(reason)) ||
       accepted!=1 || std::strcmp(reason,"fictional-player-accepted")!=0)
        return 19;
    auto malformed_cookie=real_cookie;
    malformed_cookie.push_back(0x42);
    if(shyt_yt_link_decode_cookie_v403(
        malformed_cookie.data(),malformed_cookie.size(),
        c_cookie,c_pub,&work))return 20;
    std::array<uint8_t,2> tiny{};
    if(shyt_yt_link_encode_ping_v403(
        5,1,2,tiny.data(),tiny.size(),&used) || used)
        return 21;
    if(shyt_yt_link_encode_data_v403(
        1,2,tiny.data(),tiny.size(),a.data(),a.size(),&used) || used)
        return 22;
    std::puts("SHYT_V403_ORIGINAL_YT_NET_LINK_AND_BBHOST_C_SHLK_DATA_COOP_CONTROL_WIRE_512_PASS");
    std::puts("Framing only. No live sockets, no identity, no unauthorized peer routing.");
    return cases==512?0:23;
}
