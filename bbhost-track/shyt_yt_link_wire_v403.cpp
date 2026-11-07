// SPDX-License-Identifier: GPL-2.0-or-later
// Pure in-process outer SHLK wire codec by calling original YT net_link.h.
// Pin to YT 1.3.1 5d2305ee611ef1e03be39ff925f0da75c9a70393.
// Only return plain frames to an authenticated caller; no network or auth here.
#include "shyt_yt_link_wire_v403.h"
#include "core/libraries/network/net_link.h"
#include <algorithm>
#include <cstring>
#include <span>
#include <vector>

namespace {
namespace YT=Libraries::Net::Link;
static_assert(YT::LinkVersion==4);
static_assert(YT::HeaderSize==9);
static_assert(YT::DataHeaderSize==15);
static_assert(static_cast<unsigned>(YT::Kind::Data)==SHYT_YT_LINK_MESSAGE_DATA_V403);
static_assert(static_cast<unsigned>(YT::Kind::Coop)==SHYT_YT_LINK_MESSAGE_COOP_V403);
static_assert(SHYT_YT_LINK_WIRE_MAX_V403==65536u);

bool frame_ok(const uint8_t* p,size_t n) noexcept {
    // P2P vport header accompanies each guest game message, never empty.
    return p && n>=4u && n<=SHYT_YT_LINK_WIRE_MAX_V403-YT::DataHeaderSize;
}
bool wire_ok(const uint8_t* p,size_t n) noexcept {
    return p && n>=YT::HeaderSize && n<=SHYT_YT_LINK_WIRE_MAX_V403;
}
bool export_wire(const std::vector<u8>& src,uint8_t* out,size_t cap,size_t* written) {
    if (!out || !written || src.empty() || src.size()>SHYT_YT_LINK_WIRE_MAX_V403 ||
        src.size()>cap) return false;
    std::memcpy(out,src.data(),src.size());
    *written=src.size();
    return true;
}
void set_zero(size_t *n) noexcept { if(n)*n=0; }
}
extern "C" int shyt_yt_link_encode_data_v403(
    uint32_t addr_nbo,uint16_t port_nbo,
    const uint8_t *frame,size_t frame_bytes,
    uint8_t *wire,size_t cap,size_t *written) {
    set_zero(written);
    if(!written || !frame_ok(frame,frame_bytes) || !wire || cap<YT::DataHeaderSize+frame_bytes)
        return 0;
    try {
        const auto raw=YT::EncodeData(addr_nbo,port_nbo,{frame,frame_bytes});
        return export_wire(raw,wire,cap,written)?1:0;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_decode_data_v403(
    const uint8_t* wire,size_t wire_bytes,
    uint32_t* addr_nbo,uint16_t* port_nbo,
    uint8_t* frame,size_t cap,size_t* frame_bytes) {
    set_zero(frame_bytes);
    if (addr_nbo)*addr_nbo=0;
    if (port_nbo)*port_nbo=0;
    if(!frame_bytes || !addr_nbo || !port_nbo || !frame ||
       !wire_ok(wire,wire_bytes) || wire_bytes<YT::DataHeaderSize+4u)
        return 0;
    try {
        const auto decoded=YT::DecodeData({wire,wire_bytes});
        if(!decoded || !frame_ok(decoded->frame.data(),decoded->frame.size()) ||
           decoded->frame.size()>cap)
            return 0;
        std::memmove(frame,decoded->frame.data(),decoded->frame.size());
        *addr_nbo=decoded->addr_nbo;
        *port_nbo=decoded->port_nbo;
        *frame_bytes=decoded->frame.size();
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_encode_coop_v403(
    const uint8_t* body,size_t body_bytes,
    uint8_t* wire,size_t cap,size_t* written) {
    set_zero(written);
    if(!written || (body_bytes && !body) ||
       body_bytes>SHYT_YT_LINK_WIRE_MAX_V403-YT::HeaderSize)
        return 0;
    try {
        const auto raw=YT::EncodeCoop({body,body_bytes});
        return export_wire(raw,wire,cap,written)?1:0;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_decode_coop_v403(
    const uint8_t* wire,size_t wire_bytes,
    uint8_t* body,size_t cap,size_t* body_bytes) {
    set_zero(body_bytes);
    if(!body_bytes || !body || !wire_ok(wire,wire_bytes))
        return 0;
    try {
        const auto decoded=YT::DecodeCoop({wire,wire_bytes});
        if(!decoded || decoded->size()>cap)
            return 0;
        if(!decoded->empty())
            std::memmove(body,decoded->data(),decoded->size());
        *body_bytes=decoded->size();
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_decode_cookie_v403(
    const uint8_t* wire,size_t wire_bytes,
    uint8_t cookie[SHYT_YT_LINK_COOKIE_V403],
    uint8_t server_pub[SHYT_YT_LINK_KEY_V403],uint8_t* work_bits) {
    if(cookie)std::memset(cookie,0,SHYT_YT_LINK_COOKIE_V403);
    if(server_pub)std::memset(server_pub,0,SHYT_YT_LINK_KEY_V403);
    if(work_bits)*work_bits=0;
    if(!cookie || !server_pub || !work_bits || !wire_ok(wire,wire_bytes) ||
       wire_bytes!=YT::HeaderSize+SHYT_YT_LINK_COOKIE_V403+1u+SHYT_YT_LINK_KEY_V403)
        return 0;
    try {
        int work=0;
        LinkAuth::Key pub{};
        const auto c=YT::DecodeCookie({wire,wire_bytes},&work,&pub);
        if(!c || work<0 || work>32)
            return 0;
        std::copy(c->begin(),c->end(),cookie);
        std::copy(pub.begin(),pub.end(),server_pub);
        *work_bits=static_cast<uint8_t>(work);
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_decode_welcome_v403(
    const uint8_t* wire,size_t wire_bytes,
    int* accepted,char* reason,size_t reason_cap) {
    if(accepted)*accepted=0;
    if(reason && reason_cap)reason[0]=0;
    if(!accepted || !reason || !reason_cap || !wire_ok(wire,wire_bytes))
        return 0;
    try {
        auto result=YT::DecodeWelcome({wire,wire_bytes});
        if(!result || result->text.size()>=reason_cap ||
           result->text.find('\0')!=std::string::npos)
            return 0;
        std::memcpy(reason,result->text.data(),result->text.size());
        reason[result->text.size()]='\0';
        *accepted=result->accepted?1:0;
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_encode_ping_v403(
    uint8_t kind,uint32_t seq,uint64_t sent_ms,
    uint8_t* wire,size_t cap,size_t* written) {
    set_zero(written);
    if(!written || !wire || (kind!=4u && kind!=5u))
        return 0;
    try {
        const auto raw=YT::Encode(static_cast<YT::Kind>(kind),YT::Ping{seq,sent_ms});
        return export_wire(raw,wire,cap,written)?1:0;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_decode_ping_v403(
    uint8_t kind,const uint8_t* wire,size_t wire_bytes,
    uint32_t* seq,uint64_t* sent_ms) {
    if(seq)*seq=0;
    if(sent_ms)*sent_ms=0;
    if(!seq || !sent_ms || (kind!=4u && kind!=5u) ||
       !wire_ok(wire,wire_bytes) || wire_bytes!=YT::HeaderSize+4u+8u)
        return 0;
    try {
        auto ping=YT::DecodePing(static_cast<YT::Kind>(kind),{wire,wire_bytes});
        if(!ping)return 0;
        *seq=ping->seq;
        *sent_ms=ping->sent_ms;
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_link_kind_v403(
    const uint8_t* wire,size_t wire_bytes) {
    if(!wire_ok(wire,wire_bytes))return 0;
    try {
        const auto kind=YT::KindOf({wire,wire_bytes});
        return kind?static_cast<int>(*kind):0;
    }catch(...){return 0;}
}
