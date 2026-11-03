// SPDX-License-Identifier: GPL-2.0-or-later
// V405: original YT GameData outer SHLK4 wire + original encrypted
// Noise NK client, now on one real BBHost C ABI path. NO OS sockets,
// EBOOT, game memory, production credentials or unauthorized P2P.
#include "shyt_yt_secure_game_data_v405.h"
#include "shyt_yt_link_wire_v403.h"
#include <array>
#include <cstdint>

namespace {
void wipe_sensitive(uint8_t* p,size_t n) noexcept {
    if (!p)return;
    // Volatile ensures the temporary decrypted packet is actually wiped
    // rather than eliminated by optimization after successful delivery.
    volatile uint8_t* v=p;
    for(size_t i=0;i<n;++i)v[i]=0;
}
void rejected(uint32_t* addr,uint16_t* port,size_t* size) noexcept {
    if(addr)*addr=0;
    if(port)*port=0;
    if(size)*size=0;
}
}
extern "C" int shyt_yt_secure_send_data_v405(
    ShytYtShlkClientV401* link,uint32_t addr_nbo,uint16_t port_nbo,
    const uint8_t* game,size_t game_bytes,uint8_t* wire,
    size_t wire_capacity,size_t* written) {
    if(written)*written=0;
    if(!link || !shyt_yt_shlk_linked_v401(link) ||
       !written || !game || !wire ||
       wire_capacity>SIZE_MAX-1u ||
       game_bytes<4u ||
       game_bytes>SHYT_YT_LINK_WIRE_MAX_V403-15u-24u)
        return 0;
    size_t plain_size=0;
    if(!shyt_yt_link_encode_data_v403(
          addr_nbo,port_nbo,game,game_bytes,
          wire,wire_capacity,&plain_size))
        return 0;
    size_t sealed_size=0;
    if(!shyt_yt_shlk_seal_v401(
         link,wire,plain_size,wire,wire_capacity,&sealed_size)) {
        wipe_sensitive(wire,plain_size);
        return 0;
    }
    *written=sealed_size;
    return 1;
}
extern "C" int shyt_yt_secure_receive_data_v405(
    ShytYtShlkClientV401* link,
    const uint8_t* wire,size_t wire_bytes,
    uint32_t* addr_nbo,uint16_t* port_nbo,
    uint8_t* game,size_t game_capacity,size_t* game_bytes) {
    rejected(addr_nbo,port_nbo,game_bytes);
    if(!link || !shyt_yt_shlk_linked_v401(link) ||
       !wire || !game || !game_bytes || !addr_nbo || !port_nbo ||
       wire_bytes<15u+4u+24u ||
       wire_bytes>SHYT_YT_LINK_WIRE_MAX_V403)
        return 0;
    // Fixed bounded scratch; no guest-specified allocation or packet
    // payload logging. The original SHLK Client::Open does integrity +
    // replay verification BEFORE any YT Data parser sees plaintext.
    std::array<uint8_t,SHYT_YT_LINK_WIRE_MAX_V403> plain{};
    size_t size=0;
    if(!shyt_yt_shlk_open_v401(
         link,wire,wire_bytes,plain.data(),plain.size(),&size)) {
        wipe_sensitive(plain.data(),plain.size());
        return 0;
    }
    const int okay=shyt_yt_link_decode_data_v403(
        plain.data(),size,addr_nbo,port_nbo,
        game,game_capacity,game_bytes);
    wipe_sensitive(plain.data(),size);
    if(!okay)rejected(addr_nbo,port_nbo,game_bytes);
    return okay;
}
