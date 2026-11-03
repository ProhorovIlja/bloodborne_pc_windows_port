// SPDX-License-Identifier: GPL-2.0-or-later
// V406: actual OS UDP loopback with ORIGINAL source-pinned YT SHLK4 wire.
// No external server, account, retail data, multicast or guest game hook.
#include "shyt_yt_udp_endpoint_v406.h"
#include "shyt_yt_link_wire_v403.h"
#include "core/libraries/network/net_link.h"
#include <array>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <thread>
#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
using test_fd=SOCKET;
using test_socklen=int;
static constexpr auto bad_fd=INVALID_SOCKET;
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
using test_fd=int;
using test_socklen=socklen_t;
static constexpr int bad_fd=-1;
#endif
namespace YT=Libraries::Net::Link;
static int failed(unsigned n) {
    std::fprintf(stderr,"SHYT_V406_LOCALHOST_ONLY_CASE_%u_FAILED\n",n);
    return static_cast<int>(n);
}
static void close_test_socket(test_fd s) {
#ifdef _WIN32
    closesocket(s);
#else
    close(s);
#endif
}
static int recv_server(test_fd s,uint8_t* bytes,size_t cap,
                       sockaddr_in* from) {
    test_socklen len=sizeof(*from);
    return recvfrom(s,reinterpret_cast<char*>(bytes),static_cast<int>(cap),
                    0,reinterpret_cast<sockaddr*>(from),&len);
}
int main() {
#ifdef _WIN32
    WSADATA ws{};
    if(WSAStartup(MAKEWORD(2,2),&ws)!=0)return failed(1);
#endif
    const test_fd server=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(server==bad_fd)return failed(2);
#ifdef _WIN32
    DWORD timeout=1500;
    if(setsockopt(server,SOL_SOCKET,SO_RCVTIMEO,
           reinterpret_cast<const char*>(&timeout),sizeof(timeout))!=0)
        return failed(3);
#else
    timeval timeout{1,500000};
    if(setsockopt(server,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))!=0)
        return failed(3);
#endif
    sockaddr_in address{};
    address.sin_family=AF_INET;
    address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    address.sin_port=htons(0);
    if(bind(server,reinterpret_cast<const sockaddr*>(&address),sizeof(address))!=0)
        return failed(4);
    test_socklen address_size=sizeof(address);
    if(getsockname(server,reinterpret_cast<sockaddr*>(&address),
                   &address_size)!=0 || !address.sin_port)
        return failed(5);
    if(shyt_yt_udp_open_v406(0,address.sin_port) ||
       shyt_yt_udp_open_v406(htonl(0xe0000001u),address.sin_port) ||
       shyt_yt_udp_open_v406(address.sin_addr.s_addr,0))
        return failed(6);
    auto* client=shyt_yt_udp_open_v406(
        address.sin_addr.s_addr,address.sin_port);
    if(!client)return failed(7);
    uint16_t local_port=0;
    if(!shyt_yt_udp_local_port_v406(client,&local_port) ||
       !local_port || local_port==htons(3658))
        return failed(8);
    const auto first=YT::Encode(YT::Kind::Ping,YT::Ping{11u,98765u});
    if(!shyt_yt_udp_send_server_v406(client,first.data(),first.size()))
        return failed(9);
    std::array<uint8_t,SHYT_YT_UDP_MAX_DATAGRAM_V406+2> incoming{};
    sockaddr_in client_sender{};
    const int first_n=recv_server(server,incoming.data(),incoming.size(),&client_sender);
    if(first_n!=static_cast<int>(first.size()) ||
       !std::equal(first.begin(),first.end(),incoming.begin()) ||
       client_sender.sin_port!=local_port)
        return failed(10);
    // Invalid or oversize outbound datagrams must be dropped before OS send.
    const std::array<uint8_t,3> not_shlk{{0xff,0xff,0xff}};
    if(shyt_yt_udp_send_server_v406(client,not_shlk.data(),not_shlk.size()))
        return failed(11);
    const test_fd impostor=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(impostor==bad_fd)return failed(12);
    sockaddr_in loopback{};
    loopback.sin_family=AF_INET;
    loopback.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    loopback.sin_port=local_port;
    // Adversary has a valid SHLK-looking header, but WRONG UDP source.
    const int spoof_sent=sendto(impostor,reinterpret_cast<const char*>(first.data()),
                                static_cast<int>(first.size()),0,
                                reinterpret_cast<const sockaddr*>(&loopback),sizeof(loopback));
    if(spoof_sent!=static_cast<int>(first.size()))return failed(13);
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
    size_t got=99;
    if(shyt_yt_udp_receive_server_v406(client,incoming.data(),incoming.size(),&got)!=0 ||
       got!=0) return failed(14);
    close_test_socket(impostor);

    LinkAuth::Cookie cookie{};
    LinkAuth::Key pub{};
    for(size_t i=0;i<cookie.size();++i)
        cookie[i]=static_cast<uint8_t>(i+17);
    for(size_t i=0;i<pub.size();++i)
        pub[i]=static_cast<uint8_t>(i+33);
    const auto original_cookie=YT::EncodeCookie(cookie,0,pub);
    const int reply=sendto(server,
        reinterpret_cast<const char*>(original_cookie.data()),
        static_cast<int>(original_cookie.size()),0,
        reinterpret_cast<const sockaddr*>(&loopback),sizeof(loopback));
    if(reply!=static_cast<int>(original_cookie.size()))
        return failed(15);
    int status=0;
    for(int retry=0;retry<200;++retry) {
        status=shyt_yt_udp_receive_server_v406(
            client,incoming.data(),incoming.size(),&got);
        if(status!=0)break;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    if(status!=1 || got!=original_cookie.size() ||
       !std::equal(original_cookie.begin(),original_cookie.end(),incoming.begin()))
        return failed(16);
    uint8_t said_cookie[16],said_pub[32],work=99;
    if(!shyt_yt_link_decode_cookie_v403(incoming.data(),got,
           said_cookie,said_pub,&work) ||
       work || !std::equal(cookie.begin(),cookie.end(),said_cookie) ||
       !std::equal(pub.begin(),pub.end(),said_pub))
        return failed(17);
    // Socket returns UNAUTHENTICATED SHLK; the caller has to verify a
    // pinned server key and the Noise NK tag before game delivery.
    if(shyt_yt_udp_receive_server_v406(client,incoming.data(),incoming.size(),&got)!=0)
        return failed(18);
    shyt_yt_udp_close_v406(client);
    close_test_socket(server);
#ifdef _WIN32
    WSACleanup();
#endif
    std::puts("SHYT_V406_REAL_WINDOWS_LINUX_UDP_LOOPBACK_PINNED_SERVER_SOURCE_PASS");
    std::puts("No production endpoint, identity, NetSync or room authorization.");
    return 0;
}
