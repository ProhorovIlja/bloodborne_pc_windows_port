// SPDX-License-Identifier: GPL-2.0-or-later
// V365: test ACTUAL Yharnam Together SHLK v4 Noise NK game/server crypto.
// Compiles exact original YT link_auth.h + link_crypto.cpp + Monocypher 4.0.3.
// Only deterministic, fictitious TEST keys and datagrams, never the owner's
// private accounts, EBOOT, server IPs or real session secrets.
// This is a local cryptographic PROTOCOL interoperability test, NOT online play.
#include "coop/link_auth.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <span>
#include <vector>

static LinkAuth::Key fictional_key_v365(std::uint8_t seed) {
    LinkAuth::Key key{};
    for(std::size_t i=0;i<key.size();++i)
        key[i]=static_cast<std::uint8_t>(seed+i*7u);
    return key;
}
static std::vector<u8> synthetic_datagram_v365(u8 kind) {
    return {0xff,0xff,0xff,0xff,'S','H','L','K',kind};
}
int main() {
    using namespace LinkAuth;
    static_assert(HeaderBytes==9);
    static_assert(TrailerBytes==24);
    static_assert(HelloClearBytes==26);
    static_assert(FirstHelloBytes==74);

    const auto static_key=ServerKeyOf(fictional_key_v365(7u));
    const Key fake_client_ephemeral=fictional_key_v365(33u);
    const Key fake_server_ephemeral=fictional_key_v365(77u);
    const auto wrong_pub=ServerKeyOf(fictional_key_v365(125u)).pub;
    Cookie cookie{};
    for(std::size_t i=0;i<cookie.size();++i)
        cookie[i]=static_cast<u8>(0x20u+i);

    // Pinned identity means a spoofed server cannot supply a different key.
    Client client;
    client.Pin(static_key.pub);
    if(client.TakeCookie(cookie,wrong_pub)) return 10;
    if(!client.TakeCookie(cookie,static_key.pub) || !client.HasCookie())
        return 11;
    if(!client.Pinned() || client.ServerKey()!=static_key.pub) return 12;

    auto plain_hello=synthetic_datagram_v365(KindHello);
    plain_hello.push_back(4); // YT protocol version 4
    plain_hello.insert(plain_hello.end(),cookie.begin(),cookie.end());
    // Innocuous invented account/build data. In a real game, the launcher
    // sends sensitive fields here only after the server's key is pinned.
    const std::array<u8,8> fake_identity{{'t','e','s','t','-','i','d','0'}};
    plain_hello.insert(plain_hello.end(),fake_identity.begin(),fake_identity.end());

    Client no_cookie;
    const auto first=no_cookie.SealHello(plain_hello,fake_client_ephemeral);
    if(first.size()!=FirstHelloBytes ||
       !std::all_of(first.begin()+HelloClearBytes,first.end(),
                    [](u8 n){return n==0;}))
        return 13;

    auto sealed=client.SealHello(plain_hello,fake_client_ephemeral);
    if(sealed.size()!=plain_hello.size()+KeyBytes+TagBytes)
        return 14;
    // Repeated hello is byte-identical, never re-encrypt a second
    // plaintext under the same Noise handshake key/nonce.
    if(client.SealHello(plain_hello,fictional_key_v365(110u))!=sealed)
        return 15;
    auto tampered_hello=sealed;
    tampered_hello.back()^=0x40u;
    std::vector<u8> server_plain;
    if(Responder::Open(static_key,tampered_hello,server_plain))
        return 16;
    auto responder=Responder::Open(static_key,sealed,server_plain);
    if(!responder || server_plain!=plain_hello) return 17;

    auto welcome_plain=synthetic_datagram_v365(KindWelcome);
    welcome_plain.push_back(1u); // accepted by this fictional server
    welcome_plain.push_back(0u); // empty welcome text
    auto answer=responder->Answer(welcome_plain,fake_server_ephemeral);

    auto bad_answer=answer.datagram;
    bad_answer.back()^=0x80u;
    if(client.Open(bad_answer) || client.Linked())
        return 18;
    auto opened_welcome=client.Open(answer.datagram);
    if(!opened_welcome || *opened_welcome!=welcome_plain || !client.Linked())
        return 19;

    // Actual SHLK4 authenticated game -> server encrypted datagram,
    // with fresh counter, original trailer, and replay rejection.
    auto forward_plain=synthetic_datagram_v365(3u); // SHLK Data
    const std::array<u8,9> fake_payload{{0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99}};
    forward_plain.insert(forward_plain.end(),fake_payload.begin(),fake_payload.end());
    auto encrypted_forward=forward_plain;
    const auto seal=client.Seal(encrypted_forward);
    if(!seal) return 20;
    encrypted_forward.insert(encrypted_forward.end(),seal->begin(),seal->end());
    if(encrypted_forward==forward_plain) return 21;
    auto original_first=encrypted_forward;
    auto server_rx=original_first;
    if(answer.session.Open(server_rx)!=Session::Verdict::Ok)
        return 22;
    server_rx.resize(server_rx.size()-TrailerBytes);
    if(server_rx!=forward_plain) return 23;
    auto replay=encrypted_forward;
    if(answer.session.Open(replay)!=Session::Verdict::Replay)
        return 24;
    auto tampered_forward=forward_plain;
    auto other_seal=client.Seal(tampered_forward);
    if(!other_seal) return 25;
    tampered_forward.insert(tampered_forward.end(),other_seal->begin(),other_seal->end());
    tampered_forward.back()^=0x01u;
    if(answer.session.Open(tampered_forward)!=Session::Verdict::BadTag)
        return 26;

    // Reverse direction uses distinct derived session key.
    auto backward_plain=synthetic_datagram_v365(3u);
    backward_plain.insert(backward_plain.end(),fake_payload.begin(),fake_payload.end());
    auto encrypted_backward=backward_plain;
    const auto trailer=answer.session.Seal(encrypted_backward);
    encrypted_backward.insert(encrypted_backward.end(),trailer.begin(),trailer.end());
    auto open_reply=client.Open(encrypted_backward);
    if(!open_reply || *open_reply!=backward_plain) return 27;
    if(client.Open(encrypted_backward)) return 28; // replay rejected

    std::puts("SHYT_V365_REAL_YT_SHLK4_NOISE_NK_HANDSHAKE_ENCRYPT_DECRYPT_REPLAY_PASS");
    std::puts("Deterministic fictional keys ONLY. No online server, real login, P2P or game boot.");
    return 0;
}
