// SPDX-License-Identifier: GPL-2.0-or-later
// V401: real YT SHLK4 Noise NK in the BBHost plugin, via original code.
// Pinned original: lKaniel/bloodborne-server 5d2305ee611ef1e03be39ff925f0da75c9a70393
// server/coop/link_auth.h 589b823ae0733e9104fcc0140726c8080ade20db
// server/coop/link_crypto.cpp b91b3affaca7e2da0a357f1a747a90246b167b79
// monocypher 4.0.3. NO sockets / remote endpoints / game code here.
#include "shyt_yt_shlk_client_v401.h"
#include "coop/link_auth.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <new>
#include <span>
#include <vector>

struct ShytYtShlkClientV401 {
    LinkAuth::Client original;
};
namespace {
bool valid_prefix(const uint8_t *p,size_t n) noexcept {
    static constexpr uint8_t prefix[]={
        0xff,0xff,0xff,0xff,'S','H','L','K'};
    return p && n>=LinkAuth::HeaderBytes &&
           std::memcmp(p,prefix,sizeof(prefix))==0;
}
bool all_zero(const uint8_t *p,size_t n) noexcept {
    if (!p) return true;
    unsigned acc=0;
    for(size_t i=0;i<n;++i)acc|=p[i];
    return acc==0;
}
void clear_out(size_t *written) noexcept {if(written)*written=0;}
}
extern "C" ShytYtShlkClientV401 *shyt_yt_shlk_new_v401(void) {
    return new(std::nothrow) ShytYtShlkClientV401{};
}
extern "C" void shyt_yt_shlk_free_v401(ShytYtShlkClientV401 *link) {
    delete link;
}
extern "C" int shyt_yt_shlk_pin_v401(
    ShytYtShlkClientV401 *link,const uint8_t pub[SHYT_YT_SHLK_KEY_V401]) {
    if(!link || !pub || all_zero(pub,SHYT_YT_SHLK_KEY_V401) ||
       link->original.Linked())
        return 0;
    try {
        LinkAuth::Key key;
        std::copy_n(pub,key.size(),key.begin());
        link->original.Pin(key);
        return 1;
    }catch(...) {return 0;}
}
extern "C" int shyt_yt_shlk_cookie_v401(
    ShytYtShlkClientV401 *link,
    const uint8_t cookie[SHYT_YT_SHLK_COOKIE_V401],
    const uint8_t server_pub[SHYT_YT_SHLK_KEY_V401]) {
    if(!link || !cookie || !server_pub ||
       all_zero(server_pub,SHYT_YT_SHLK_KEY_V401))return 0;
    try {
        LinkAuth::Cookie c;
        LinkAuth::Key key;
        std::copy_n(cookie,c.size(),c.begin());
        std::copy_n(server_pub,key.size(),key.begin());
        return link->original.TakeCookie(c,key)?1:0;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_shlk_hello_v401(
    ShytYtShlkClientV401 *link,const uint8_t *plain,size_t plain_len,
    const uint8_t fresh_ephemeral[SHYT_YT_SHLK_KEY_V401],
    uint8_t *wire,size_t cap,size_t *written) {
    clear_out(written);
    if(!written || !link || !plain || !wire || !fresh_ephemeral ||
       plain_len<LinkAuth::HelloClearBytes ||
       plain_len>SHYT_YT_SHLK_MAX_WIRE_V401-64u ||
       cap<plain_len+LinkAuth::HelloSealBytes ||
       !valid_prefix(plain,plain_len) ||
       plain[LinkAuth::KindAt]!=LinkAuth::KindHello ||
       plain[LinkAuth::HeaderBytes]!=4u ||
       all_zero(fresh_ephemeral,SHYT_YT_SHLK_KEY_V401))
        return 0;
    // Zero secret-bearing payload is mandatory before a cookie arrives.
    if(!link->original.HasCookie() && plain_len!=LinkAuth::HelloClearBytes)
        return 0;
    if(link->original.HasCookie() &&
       !std::equal(link->original.CookieToEcho().begin(),
                   link->original.CookieToEcho().end(),
                   plain+LinkAuth::HeaderBytes+1))
        return 0;
    try {
        LinkAuth::Key fresh{};
        std::copy_n(fresh_ephemeral,fresh.size(),fresh.begin());
        const auto sealed=link->original.SealHello(
            {plain,plain_len},fresh);
        if(sealed.size()>cap || sealed.size()>SHYT_YT_SHLK_MAX_WIRE_V401)
            return 0;
        std::copy(sealed.begin(),sealed.end(),wire);
        *written=sealed.size();
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_shlk_open_v401(
    ShytYtShlkClientV401 *link,const uint8_t *wire,size_t size,
    uint8_t *plain,size_t cap,size_t *written) {
    clear_out(written);
    if(!written || !link || !wire || !plain ||
       size>SHYT_YT_SHLK_MAX_WIRE_V401 ||
       !valid_prefix(wire,size) || cap<size)
        return 0;
    try {
        auto result=link->original.Open({wire,size});
        if(!result || result->size()>cap) return 0;
        std::copy(result->begin(),result->end(),plain);
        *written=result->size();
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_shlk_seal_v401(
    ShytYtShlkClientV401 *link,const uint8_t *plain,size_t size,
    uint8_t *wire,size_t cap,size_t *written) {
    clear_out(written);
    if(!written || !link || !link->original.Linked() ||
       !plain || !wire || !valid_prefix(plain,size) ||
       size>SHYT_YT_SHLK_MAX_WIRE_V401-LinkAuth::TrailerBytes ||
       cap<size+LinkAuth::TrailerBytes)
        return 0;
    try {
        std::vector<uint8_t> frame(plain,plain+size);
        auto tag=link->original.Seal(frame);
        if(!tag) return 0;
        frame.insert(frame.end(),tag->begin(),tag->end());
        if(frame.size()>cap || frame.size()>SHYT_YT_SHLK_MAX_WIRE_V401)
            return 0;
        std::copy(frame.begin(),frame.end(),wire);
        *written=frame.size();
        return 1;
    }catch(...){return 0;}
}
extern "C" int shyt_yt_shlk_linked_v401(
    const ShytYtShlkClientV401 *link) {
    return link && link->original.Linked()?1:0;
}
