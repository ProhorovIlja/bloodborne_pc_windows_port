// SPDX-License-Identifier: GPL-2.0-or-later
// V405: run the REAL YT source-pinned Server Responder/session against
// BBHost client C ABI, outer Data wire, and authenticated game bytes.
// Synthetic samples ONLY. Never connects to a server or handles secrets.
#include "shyt_yt_secure_game_data_v405.h"
#include "shyt_yt_shlk_client_v401.h"
#include "core/libraries/network/net_link.h"
#include "coop/link_auth.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

namespace YT=Libraries::Net::Link;
static LinkAuth::Key fake_key(uint8_t seed) {
    LinkAuth::Key k{};
    for(size_t i=0;i<k.size();++i)k[i]=static_cast<uint8_t>(seed+i*7u);
    return k;
}
static uint32_t rnd(uint32_t& state) {
    state^=state<<13;state^=state>>17;state^=state<<5;return state;
}
static int fail_case_v405(unsigned code) {
    std::fprintf(stderr,"SHYT_V405_SYNTHETIC_ONLY_TEST_CASE_%u_FAILED\n",code);
    return static_cast<int>(code);
}
int main() {
    const auto server=LinkAuth::ServerKeyOf(fake_key(17));
    LinkAuth::Cookie cookie{};
    for(size_t i=0;i<cookie.size();++i)
        cookie[i]=static_cast<u8>(i+20u);
    ShytYtShlkClientV401* client=shyt_yt_shlk_new_v401();
    if(!client)return fail_case_v405(1);
    std::array<uint8_t,65536> wire{},received{};
    const std::array<u8,8> fake_header{{0xff,0xff,0xff,0xff,'S','H','L','K'}};
    const std::array<uint8_t,8> fictitious_p2p{{
        0xff,0xff,0xff,0xff,0x31,0x32,0x33,0x34}};
    size_t sent=99;
    if(shyt_yt_secure_send_data_v405(client,0x01020304u,3658u,
          fictitious_p2p.data(),fictitious_p2p.size(),
          wire.data(),wire.size(),&sent) || sent)
        return fail_case_v405(2);
    if(!shyt_yt_shlk_pin_v401(client,server.pub.data()) ||
       !shyt_yt_shlk_cookie_v401(client,cookie.data(),server.pub.data()))
        return fail_case_v405(3);
    YT::Hello hello{};
    hello.online_id="fictional-hunter";
    hello.build="fictional-109";
    hello.secret="fictional-test-secret";
    hello.cookie=cookie;
    const auto plain_hello=YT::Encode(hello);
    if(plain_hello.size()<LinkAuth::HelloClearBytes ||
       !std::equal(fake_header.begin(),fake_header.end(),plain_hello.begin()))
        return fail_case_v405(4);
    const auto fresh=fake_key(47);
    if(!shyt_yt_shlk_hello_v401(client,
         plain_hello.data(),plain_hello.size(),fresh.data(),
         wire.data(),wire.size(),&sent))
        return fail_case_v405(5);
    std::vector<u8> incoming(wire.begin(),wire.begin()+sent);
    std::vector<u8> clear;
    auto responder=LinkAuth::Responder::Open(server,incoming,clear);
    if(!responder || clear!=plain_hello)
        return fail_case_v405(6);
    const auto welcome=YT::Encode(YT::Welcome{true,"fictional-session"});
    auto answer=responder->Answer(welcome,fake_key(71));
    if(!shyt_yt_shlk_open_v401(client,
         answer.datagram.data(),answer.datagram.size(),
         received.data(),received.size(),&sent) ||
       sent!=welcome.size() || !shyt_yt_shlk_linked_v401(client))
        return fail_case_v405(7);
    uint32_t rng=0x17549AC3u;
    for(unsigned i=0;i<256u;++i) {
        // Game's actual vport header, all OTHER bytes fictional.
        std::vector<uint8_t> p2p(4u+(i*17u)%1711u,0);
        for(size_t j=4;j<p2p.size();++j)
            p2p[j]=static_cast<uint8_t>(rnd(rng)>>24);
        p2p[0]=p2p[1]=p2p[2]=p2p[3]=0xff;
        uint32_t sender_addr=rnd(rng);
        uint16_t sender_port=static_cast<uint16_t>(rnd(rng));
        size_t n=0;
        if(!shyt_yt_secure_send_data_v405(client,
              sender_addr,sender_port,p2p.data(),p2p.size(),
              wire.data(),wire.size(),&n) || n<24u+15u+4u)
            return fail_case_v405(8);
        const auto sealed=std::vector<uint8_t>(wire.begin(),wire.begin()+n);
        // SHLK's outer 4-byte signaling vport header is the SAME as
        // the guest P2P header. Compare complete original YT Data
        // PLAINTEXT against ciphertext, never the first 4 bytes alone.
        const auto original_plain=YT::EncodeData(sender_addr,sender_port,p2p);
        if(sealed.size()!=original_plain.size()+LinkAuth::TrailerBytes ||
           std::equal(original_plain.begin(),original_plain.end(),sealed.begin()))
            return fail_case_v405(9);
        auto server_open=sealed;
        if(answer.session.Open(server_open)!=LinkAuth::Session::Verdict::Ok)
            return fail_case_v405(10);
        server_open.resize(server_open.size()-LinkAuth::TrailerBytes);
        auto original_data=YT::DecodeData(server_open);
        if(!original_data ||
           original_data->addr_nbo!=sender_addr ||
           original_data->port_nbo!=sender_port ||
           original_data->frame.size()!=p2p.size() ||
           !std::equal(original_data->frame.begin(),
                       original_data->frame.end(),p2p.begin()))
            return fail_case_v405(11);
        auto repeated=sealed;
        if(answer.session.Open(repeated)!=LinkAuth::Session::Verdict::Replay)
            return fail_case_v405(12);
        // Reverse server-to-BBHost direction with its real original YT
        // Noise NK session (server room policy still not implemented).
        auto from_server=YT::EncodeData(sender_addr,sender_port,p2p);
        auto trailer=answer.session.Seal(from_server);
        from_server.insert(from_server.end(),trailer.begin(),trailer.end());
        uint32_t decoded_addr=0;uint16_t decoded_port=0;
        size_t decoded_size=0;
        if(!shyt_yt_secure_receive_data_v405(client,
               from_server.data(),from_server.size(),
               &decoded_addr,&decoded_port,received.data(),
               received.size(),&decoded_size) ||
           decoded_addr!=sender_addr || decoded_port!=sender_port ||
           decoded_size!=p2p.size() ||
           std::memcmp(received.data(),p2p.data(),decoded_size)!=0)
            return fail_case_v405(13);
        if(shyt_yt_secure_receive_data_v405(client,
            from_server.data(),from_server.size(),&decoded_addr,
            &decoded_port,received.data(),received.size(),&decoded_size) ||
           decoded_size || decoded_addr || decoded_port)
            return fail_case_v405(14);
        auto damaged=YT::EncodeData(sender_addr,sender_port,p2p);
        auto next_tag=answer.session.Seal(damaged);
        damaged.insert(damaged.end(),next_tag.begin(),next_tag.end());
        damaged.back()^=0x80;
        if(shyt_yt_secure_receive_data_v405(client,
            damaged.data(),damaged.size(),&decoded_addr,
            &decoded_port,received.data(),received.size(),&decoded_size) ||
           decoded_size || decoded_addr || decoded_port)
            return fail_case_v405(15);
        if(shyt_yt_secure_send_data_v405(client,sender_addr,sender_port,
             p2p.data(),p2p.size(),wire.data(),16u,&n) || n)
            return fail_case_v405(16);
    }
    shyt_yt_shlk_free_v401(client);
    std::puts("SHYT_V405_ORIGINAL_YT_SERVER_VS_BBHOST_AUTHENTICATED_GAMEDATA_256_ROUNDS_PASS");
    std::puts("All tests purely fictional; actual live UDP server and game P2P not connected.");
    return 0;
}
