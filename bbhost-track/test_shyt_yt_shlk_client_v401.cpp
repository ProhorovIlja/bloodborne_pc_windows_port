// SPDX-License-Identifier: GPL-2.0-or-later
// Actual original YT responder on one side, new BBHost C client ABI on other.
// All deterministic keys are FICTIONAL TEST VECTORS only; never use these
// as real identities or protocol ephemeral randomness in production.
#include "shyt_yt_shlk_client_v401.h"
#include "coop/link_auth.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

static LinkAuth::Key fake_key(std::uint8_t initial) {
    LinkAuth::Key v{};
    for(std::size_t i=0;i<v.size();++i) v[i]=initial+static_cast<u8>(i*7);
    return v;
}
static std::vector<u8> header(u8 kind) {
    return {0xff,0xff,0xff,0xff,'S','H','L','K',kind};
}
int main() {
    using namespace LinkAuth;
    const auto server=ServerKeyOf(fake_key(17));
    const auto intruder=ServerKeyOf(fake_key(71));
    Cookie cookie{};
    for(unsigned i=0;i<cookie.size();++i)
        cookie[i]=static_cast<u8>(i+20);
    auto *bb=shyt_yt_shlk_new_v401();
    if(!bb || shyt_yt_shlk_linked_v401(bb)) return 1;
    if(!shyt_yt_shlk_pin_v401(bb,server.pub.data())) return 2;
    if(shyt_yt_shlk_cookie_v401(bb,cookie.data(),intruder.pub.data()))
        return 3;
    if(!shyt_yt_shlk_cookie_v401(bb,cookie.data(),server.pub.data()))
        return 4;
    auto hello=header(KindHello);
    hello.push_back(4);
    hello.insert(hello.end(),cookie.begin(),cookie.end());
    const std::array<u8,12> fictional_identity={
        'f','i','c','t','i','o','n','a','l','-','0','1'};
    hello.insert(hello.end(),fictional_identity.begin(),fictional_identity.end());

    // Emulate exactly the original YT v1.3.1 sender and compare wire.
    const auto fresh=fake_key(45);
    Client original;
    original.Pin(server.pub);
    if(!original.TakeCookie(cookie,server.pub))return 5;
    const auto exact=original.SealHello(hello,fresh);
    std::array<std::uint8_t,65536> output{};
    size_t n=99;
    if(!shyt_yt_shlk_hello_v401(bb,hello.data(),hello.size(),fresh.data(),
                               output.data(),output.size(),&n) ||
       n!=exact.size() || !std::equal(exact.begin(),exact.end(),output.begin()))
        return 6;
    // Retransmission under pending handshake must be identical.
    const auto second=fake_key(91);
    if(!shyt_yt_shlk_hello_v401(bb,hello.data(),hello.size(),second.data(),
                               output.data(),output.size(),&n) ||
       n!=exact.size() || !std::equal(exact.begin(),exact.end(),output.begin()))
        return 7;
    const auto bad_hello=std::vector<u8>(output.begin(),output.begin()+n);
    auto damaged=bad_hello;
    damaged.back()^=0x80;
    std::vector<u8> opened;
    if(Responder::Open(server,damaged,opened))return 8;
    auto responder=Responder::Open(server,bad_hello,opened);
    if(!responder || opened!=hello)return 9;

    auto welcome=header(KindWelcome);
    welcome.push_back(1);
    welcome.push_back(0);
    auto response=responder->Answer(welcome,fake_key(63));
    auto invalid_welcome=response.datagram;
    invalid_welcome.back()^=0x40;
    if(shyt_yt_shlk_open_v401(bb,invalid_welcome.data(),invalid_welcome.size(),
                              output.data(),output.size(),&n) ||
       n!=0 || shyt_yt_shlk_linked_v401(bb))
        return 10;
    if(!shyt_yt_shlk_open_v401(bb,response.datagram.data(),
                              response.datagram.size(),
                              output.data(),output.size(),&n) ||
       n!=welcome.size() ||
       !std::equal(welcome.begin(),welcome.end(),output.begin()) ||
       !shyt_yt_shlk_linked_v401(bb))
        return 11;
    auto outgoing=header(3); // Synthetic SHLK data-type packet
    outgoing.insert(outgoing.end(),fictional_identity.begin(),
                    fictional_identity.end());
    if(!shyt_yt_shlk_seal_v401(bb,outgoing.data(),outgoing.size(),
                              output.data(),output.size(),&n))
        return 12;
    auto transport=std::vector<u8>(output.begin(),output.begin()+n);
    auto opened_transport=transport;
    if(response.session.Open(opened_transport)!=Session::Verdict::Ok)
        return 13;
    opened_transport.resize(opened_transport.size()-TrailerBytes);
    if(opened_transport!=outgoing)return 14;
    auto replay=transport;
    if(response.session.Open(replay)!=Session::Verdict::Replay)
        return 15;
    auto encrypted_response=outgoing;
    const auto trailer=response.session.Seal(encrypted_response);
    encrypted_response.insert(encrypted_response.end(),
                              trailer.begin(),trailer.end());
    if(!shyt_yt_shlk_open_v401(bb,encrypted_response.data(),
                              encrypted_response.size(),
                              output.data(),output.size(),&n) ||
       n!=outgoing.size() ||
       !std::equal(outgoing.begin(),outgoing.end(),output.begin()))
        return 16;
    if(shyt_yt_shlk_open_v401(bb,encrypted_response.data(),
                             encrypted_response.size(),
                             output.data(),output.size(),&n) || n!=0)
        return 17;
    // No link data before auth, no tiny buffers, no invalid header.
    std::array<u8,1> tiny{};
    if(shyt_yt_shlk_seal_v401(bb,outgoing.data(),outgoing.size(),
                             tiny.data(),tiny.size(),&n) || n!=0)
        return 18;
    auto wrong_header=outgoing;
    wrong_header[4]='X';
    if(shyt_yt_shlk_seal_v401(bb,wrong_header.data(),wrong_header.size(),
                             output.data(),output.size(),&n) || n!=0)
        return 19;
    shyt_yt_shlk_free_v401(bb);
    std::puts("SHYT_V401_ACTUAL_YT_SHLK4_ORIGINAL_RESPONDER_BBHOST_C_CLIENT_INTEROP_PASS");
    std::puts("Isolated source-only protocol interop; NO socket, live server, login, P2P or game boot.");
    return 0;
}
