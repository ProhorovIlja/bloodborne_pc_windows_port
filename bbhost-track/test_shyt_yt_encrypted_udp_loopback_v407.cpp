// SPDX-License-Identifier: GPL-2.0-or-later
// V407: REAL OS UDP / REAL original YT SHLK4 Noise NK server responder
// / REAL BBHost V401+V403+V405+V406 transport, 100% local invented data.
// No account credentials, owner server, game binary or production traffic.
#include "shyt_yt_shlk_client_v401.h"
#include "shyt_yt_link_wire_v403.h"
#include "shyt_yt_secure_game_data_v405.h"
#include "shyt_yt_udp_endpoint_v406.h"
#include "core/libraries/network/net_link.h"
#include "coop/link_auth.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <thread>
#include <vector>
#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
using raw_fd=SOCKET;
using raw_len=int;
static constexpr raw_fd bad_fd=INVALID_SOCKET;
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
using raw_fd=int;
using raw_len=socklen_t;
static constexpr raw_fd bad_fd=-1;
#endif
namespace YT=Libraries::Net::Link;
static int fail(unsigned n) {
    std::fprintf(stderr,"SHYT_V407_LOCAL_ONLY_ENCRYPTED_UDP_CASE_%u_FAILED\n",n);
    return static_cast<int>(n);
}
static void close_fd(raw_fd fd) {
#ifdef _WIN32
    closesocket(fd);
#else
    close(fd);
#endif
}
static std::array<u8,32> fake_key(unsigned salt) {
    std::array<u8,32> b{};
    for(size_t i=0;i<b.size();++i)
        b[i]=static_cast<u8>(salt+i*3u);
    return b;
}
static int socket_recv(raw_fd fd,uint8_t* out,size_t cap,sockaddr_in* sender) {
    raw_len n=sizeof(*sender);
    return recvfrom(fd,reinterpret_cast<char*>(out),static_cast<int>(cap),
                    0,reinterpret_cast<sockaddr*>(sender),&n);
}
static bool socket_send(raw_fd fd,const sockaddr_in& peer,
                        const std::vector<u8>& bytes) {
    return sendto(fd,reinterpret_cast<const char*>(bytes.data()),
                  static_cast<int>(bytes.size()),0,
                  reinterpret_cast<const sockaddr*>(&peer),
                  sizeof(peer))==static_cast<int>(bytes.size());
}
static int await_client(ShytYtUdpEndpointV406* link,
                        uint8_t* out,size_t cap,size_t* got) {
    for(int i=0;i<200;++i) {
        int result=shyt_yt_udp_receive_server_v406(link,out,cap,got);
        if(result!=0)return result;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    return 0;
}
int main() {
#ifdef _WIN32
    WSADATA winsock{};
    if(WSAStartup(MAKEWORD(2,2),&winsock)!=0)return fail(1);
#endif
    const raw_fd server_fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(server_fd==bad_fd)return fail(2);
#ifdef _WIN32
    DWORD timeout=1500;
    if(setsockopt(server_fd,SOL_SOCKET,SO_RCVTIMEO,
          reinterpret_cast<const char*>(&timeout),sizeof(timeout))!=0)
        return fail(3);
#else
    timeval timeout{1,500000};
    if(setsockopt(server_fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))!=0)
        return fail(3);
#endif
    sockaddr_in server_addr{};
    server_addr.sin_family=AF_INET;
    server_addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    server_addr.sin_port=htons(0);
    if(bind(server_fd,reinterpret_cast<const sockaddr*>(&server_addr),
            sizeof(server_addr))!=0)return fail(4);
    raw_len server_len=sizeof(server_addr);
    if(getsockname(server_fd,reinterpret_cast<sockaddr*>(&server_addr),
                   &server_len)!=0)return fail(5);
    auto* udp=shyt_yt_udp_open_v406(
        server_addr.sin_addr.s_addr,server_addr.sin_port);
    auto* client=shyt_yt_shlk_new_v401();
    if(!udp || !client)return fail(6);
    const auto server_key=LinkAuth::ServerKeyOf(fake_key(19));
    if(!shyt_yt_shlk_pin_v401(client,server_key.pub.data()))
        return fail(7);

    // Real YT first Hello (without cookie) is 74 bytes with a zeroed
    // clear header region: it MUST NOT reveal account/build/secret.
    std::array<uint8_t,26> initial{};
    initial[0]=initial[1]=initial[2]=initial[3]=0xff;
    initial[4]='S';initial[5]='H';initial[6]='L';initial[7]='K';
    initial[8]=1;initial[9]=4;
    std::array<uint8_t,2048> encrypted{};
    size_t bytes=0;
    const auto initial_ephemeral=fake_key(37);
    if(!shyt_yt_shlk_hello_v401(
        client,initial.data(),initial.size(),initial_ephemeral.data(),
        encrypted.data(),encrypted.size(),&bytes) ||
       bytes!=LinkAuth::FirstHelloBytes ||
       !std::all_of(encrypted.begin()+LinkAuth::HelloClearBytes,
                    encrypted.begin()+bytes,[](u8 n){return n==0;}))
        return fail(8);
    if(!shyt_yt_udp_send_server_v406(udp,encrypted.data(),bytes))
        return fail(9);
    std::array<uint8_t,2048> server_rx{};
    sockaddr_in client_addr{};
    const int n1=socket_recv(server_fd,server_rx.data(),server_rx.size(),&client_addr);
    if(n1!=static_cast<int>(bytes) ||
       !std::equal(encrypted.begin(),encrypted.begin()+bytes,server_rx.begin()))
        return fail(10);

    LinkAuth::Cookie cookie{};
    for(size_t i=0;i<cookie.size();++i)
        cookie[i]=static_cast<u8>(i+51u);
    const auto reply_cookie=YT::EncodeCookie(cookie,0,server_key.pub);
    if(!socket_send(server_fd,client_addr,reply_cookie))return fail(11);
    size_t client_bytes=0;
    if(await_client(udp,encrypted.data(),encrypted.size(),&client_bytes)!=1)
        return fail(12);
    uint8_t said_cookie[16],said_key[32],work=99;
    if(!shyt_yt_link_decode_cookie_v403(
        encrypted.data(),client_bytes,said_cookie,said_key,&work) ||
       work || !std::equal(cookie.begin(),cookie.end(),said_cookie) ||
       !std::equal(server_key.pub.begin(),server_key.pub.end(),said_key) ||
       !shyt_yt_shlk_cookie_v401(client,said_cookie,said_key))
        return fail(13);

    YT::Hello hello{};
    hello.cookie=cookie;
    hello.online_id="synthetic-hunter";
    hello.build="synthetic-bloodborne-build";
    hello.secret="synthetic-secret-never-real";
    const auto plain_hello=YT::Encode(hello);
    const auto next_ephemeral=fake_key(71);
    if(!shyt_yt_shlk_hello_v401(
        client,plain_hello.data(),plain_hello.size(),next_ephemeral.data(),
        encrypted.data(),encrypted.size(),&bytes) ||
       !shyt_yt_udp_send_server_v406(udp,encrypted.data(),bytes))
        return fail(14);
    const int n2=socket_recv(server_fd,server_rx.data(),server_rx.size(),&client_addr);
    if(n2!=static_cast<int>(bytes))return fail(15);
    std::vector<u8> decoded_hello;
    auto response=LinkAuth::Responder::Open(
        server_key,{server_rx.data(),static_cast<size_t>(n2)},decoded_hello);
    if(!response || decoded_hello!=plain_hello)return fail(16);
    const auto welcome=YT::Encode(YT::Welcome{true,"fictional-accepted"});
    auto answer=response->Answer(welcome,fake_key(99));
    if(!socket_send(server_fd,client_addr,answer.datagram))
        return fail(17);
    if(await_client(udp,encrypted.data(),encrypted.size(),&client_bytes)!=1)
        return fail(18);
    std::array<uint8_t,2048> welcome_plain{};
    if(!shyt_yt_shlk_open_v401(
        client,encrypted.data(),client_bytes,
        welcome_plain.data(),welcome_plain.size(),&bytes) ||
       !shyt_yt_shlk_linked_v401(client) ||
       !YT::DecodeWelcome({welcome_plain.data(),bytes}) ||
       !YT::DecodeWelcome({welcome_plain.data(),bytes})->accepted)
        return fail(19);

    const std::array<uint8_t,12> fake_game{{
        0xff,0xff,0xff,0xff,0x31,0x32,0x33,0x34,0x25,0x26,0x27,0x28}};
    constexpr uint32_t virtual_addr=0x12345678u;
    constexpr uint16_t virtual_port=0x4a5bu;
    if(!shyt_yt_secure_send_data_v405(
          client,virtual_addr,virtual_port,fake_game.data(),fake_game.size(),
          encrypted.data(),encrypted.size(),&bytes) ||
       !shyt_yt_udp_send_server_v406(udp,encrypted.data(),bytes))
        return fail(20);
    const int n3=socket_recv(server_fd,server_rx.data(),server_rx.size(),&client_addr);
    if(n3!=static_cast<int>(bytes))return fail(21);
    std::vector<u8> opened_packet(server_rx.begin(),server_rx.begin()+n3);
    if(answer.session.Open(opened_packet)!=LinkAuth::Session::Verdict::Ok)
        return fail(22);
    opened_packet.resize(opened_packet.size()-LinkAuth::TrailerBytes);
    auto game_data=YT::DecodeData(opened_packet);
    if(!game_data || game_data->addr_nbo!=virtual_addr ||
       game_data->port_nbo!=virtual_port ||
       game_data->frame.size()!=fake_game.size() ||
       !std::equal(game_data->frame.begin(),game_data->frame.end(),
                   fake_game.begin()))
        return fail(23);

    auto from_server=YT::EncodeData(virtual_addr,virtual_port,fake_game);
    const auto trailer=answer.session.Seal(from_server);
    from_server.insert(from_server.end(),trailer.begin(),trailer.end());
    if(!socket_send(server_fd,client_addr,from_server))return fail(24);
    if(await_client(udp,encrypted.data(),encrypted.size(),&client_bytes)!=1)
        return fail(25);
    uint32_t from_addr=0;uint16_t from_port=0;
    std::array<uint8_t,2048> game_output{};
    size_t result_size=0;
    if(!shyt_yt_secure_receive_data_v405(
         client,encrypted.data(),client_bytes,&from_addr,&from_port,
         game_output.data(),game_output.size(),&result_size) ||
       from_addr!=virtual_addr || from_port!=virtual_port ||
       result_size!=fake_game.size() ||
       !std::equal(fake_game.begin(),fake_game.end(),game_output.begin()))
        return fail(26);
    // Authentic server but previously seen packet is still replayed.
    if(!socket_send(server_fd,client_addr,from_server))return fail(27);
    if(await_client(udp,encrypted.data(),encrypted.size(),&client_bytes)!=1 ||
       shyt_yt_secure_receive_data_v405(
           client,encrypted.data(),client_bytes,&from_addr,&from_port,
           game_output.data(),game_output.size(),&result_size) ||
       result_size!=0)
        return fail(28);
    shyt_yt_shlk_free_v401(client);
    shyt_yt_udp_close_v406(udp);
    close_fd(server_fd);
#ifdef _WIN32
    WSACleanup();
#endif
    std::puts("SHYT_V407_REAL_OS_UDP_AND_ORIGINAL_YT_NOISE4_ENCRYPTED_GAMEDATA_PASS");
    std::puts("LOCALHOST ONLY; no retail game, real server, direct peer or gameplay hook.");
    return 0;
}
