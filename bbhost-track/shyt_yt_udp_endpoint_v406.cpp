// SPDX-License-Identifier: GPL-2.0-or-later
// V406: one native UDP endpoint, no relay trust or game injections.
// Uses OS-assigned local port, no SO_REUSEADDR and no second reader
// bound to BBHost's guest P2P port 3658. No background threads.
#include "shyt_yt_udp_endpoint_v406.h"
#include "shyt_yt_link_wire_v403.h"
#include <array>
#include <cstring>
#include <new>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
using native_socket_v406=SOCKET;
static constexpr native_socket_v406 bad_socket_v406=INVALID_SOCKET;
using native_socklen_v406=int;
#else
#include <arpa/inet.h>
#include <cerrno>
#include <fcntl.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
using native_socket_v406=int;
static constexpr native_socket_v406 bad_socket_v406=-1;
using native_socklen_v406=socklen_t;
#endif

struct ShytYtUdpEndpointV406 {
    native_socket_v406 fd=bad_socket_v406;
    sockaddr_in server{};
#ifdef _WIN32
    bool winsock_started=false;
#endif
};

namespace {
void close_native_v406(native_socket_v406 fd) noexcept {
    if(fd==bad_socket_v406)return;
#ifdef _WIN32
    closesocket(fd);
#else
    close(fd);
#endif
}
bool endpoint_valid_v406(uint32_t ip_nbo,uint16_t port_nbo) noexcept {
    if(!port_nbo || !ip_nbo)return false;
    const uint32_t ip=ntohl(ip_nbo);
    const unsigned first=ip>>24;
    // No wildcard, reserved, multicast or broadcast public target.
    if(first==0u || first>=224u || ip==0xffffffffu)
        return false;
    // Refuse IPv4 directed-broadcast destinations as well. A .255
    // host can in theory be valid on a /31 but isn't suitable for this
    // single-server YT handshake transport.
    if((ip&0xffu)==0xffu)return false;
    return true;
}
bool make_nonblocking_v406(native_socket_v406 fd) noexcept {
#ifdef _WIN32
    u_long on=1u;
    return ioctlsocket(fd,FIONBIO,&on)==0;
#else
    const int flags=fcntl(fd,F_GETFL,0);
    return flags>=0 && fcntl(fd,F_SETFL,flags|O_NONBLOCK)==0;
#endif
}
bool transient_v406() noexcept {
#ifdef _WIN32
    const int e=WSAGetLastError();
    return e==WSAEWOULDBLOCK || e==WSAEINTR;
#else
    return errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK;
#endif
}
}
extern "C" ShytYtUdpEndpointV406 *shyt_yt_udp_open_v406(
    uint32_t server_ipv4_nbo,uint16_t server_port_nbo) {
    if(!endpoint_valid_v406(server_ipv4_nbo,server_port_nbo))
        return nullptr;
    auto* endpoint=new(std::nothrow) ShytYtUdpEndpointV406{};
    if(!endpoint)return nullptr;
#ifdef _WIN32
    WSADATA info{};
    if(WSAStartup(MAKEWORD(2,2),&info)!=0) {
        delete endpoint;
        return nullptr;
    }
    endpoint->winsock_started=true;
#endif
    endpoint->fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(endpoint->fd==bad_socket_v406 ||
       !make_nonblocking_v406(endpoint->fd)) {
        shyt_yt_udp_close_v406(endpoint);
        return nullptr;
    }
    sockaddr_in local{};
    local.sin_family=AF_INET;
    local.sin_addr.s_addr=htonl(INADDR_ANY);
    local.sin_port=htons(0);
    if(bind(endpoint->fd,reinterpret_cast<const sockaddr*>(&local),
            sizeof(local))!=0) {
        shyt_yt_udp_close_v406(endpoint);
        return nullptr;
    }
    endpoint->server.sin_family=AF_INET;
    endpoint->server.sin_addr.s_addr=server_ipv4_nbo;
    endpoint->server.sin_port=server_port_nbo;
    return endpoint;
}
extern "C" void shyt_yt_udp_close_v406(ShytYtUdpEndpointV406 *endpoint) {
    if(!endpoint)return;
    close_native_v406(endpoint->fd);
#ifdef _WIN32
    if(endpoint->winsock_started)WSACleanup();
#endif
    delete endpoint;
}
extern "C" int shyt_yt_udp_local_port_v406(
    const ShytYtUdpEndpointV406* endpoint,uint16_t *port_nbo) {
    if(port_nbo)*port_nbo=0;
    if(!endpoint || !port_nbo || endpoint->fd==bad_socket_v406)
        return 0;
    sockaddr_in bound{};
    native_socklen_v406 len=sizeof(bound);
    if(getsockname(endpoint->fd,reinterpret_cast<sockaddr*>(&bound),&len)!=0 ||
       bound.sin_family!=AF_INET || !bound.sin_port)
        return 0;
    *port_nbo=bound.sin_port;
    return 1;
}
extern "C" int shyt_yt_udp_send_server_v406(
    ShytYtUdpEndpointV406* endpoint,const uint8_t* packet,size_t size) {
    if(!endpoint || endpoint->fd==bad_socket_v406 || !packet ||
       !size || size>SHYT_YT_UDP_MAX_DATAGRAM_V406 ||
       !shyt_yt_link_kind_v403(packet,size))
        return 0;
    const int n=sendto(endpoint->fd,reinterpret_cast<const char*>(packet),
                       static_cast<int>(size),0,
                       reinterpret_cast<const sockaddr*>(&endpoint->server),
                       sizeof(endpoint->server));
    return n==static_cast<int>(size)?1:0;
}
extern "C" int shyt_yt_udp_receive_server_v406(
    ShytYtUdpEndpointV406* endpoint,
    uint8_t* packet,size_t packet_capacity,size_t* got) {
    if(got)*got=0;
    if(!endpoint || endpoint->fd==bad_socket_v406 ||
       !packet || !got || packet_capacity==0)
        return -1;
    std::array<uint8_t,SHYT_YT_UDP_MAX_DATAGRAM_V406+1u> incoming{};
    sockaddr_in sender{};
    native_socklen_v406 len=sizeof(sender);
    const int n=recvfrom(endpoint->fd,
        reinterpret_cast<char*>(incoming.data()),
        static_cast<int>(incoming.size()),0,
        reinterpret_cast<sockaddr*>(&sender),&len);
    if(n<0) return transient_v406()?0:-1;
    if(n<9 || n>static_cast<int>(SHYT_YT_UDP_MAX_DATAGRAM_V406) ||
       sender.sin_family!=AF_INET ||
       sender.sin_addr.s_addr!=endpoint->server.sin_addr.s_addr ||
       sender.sin_port!=endpoint->server.sin_port ||
       static_cast<size_t>(n)>packet_capacity ||
       !shyt_yt_link_kind_v403(incoming.data(),static_cast<size_t>(n)))
        return 0; // No logging or exposure of untrusted third-party UDP.
    std::memcpy(packet,incoming.data(),static_cast<size_t>(n));
    *got=static_cast<size_t>(n);
    return 1; // NOT authenticated: caller MUST invoke original Noise NK.
}
