// SPDX-License-Identifier: GPL-2.0-or-later
// V325: real Linux UDP loopback STUN exchange on the game's own
// originating socket. No public STUN server, NAT, Internet, game file,
// or P2P authorization is involved; tests wire reachability only.
#include "yt_reflexive_stun_v321.h"
#include "hybrid_direct_physical_gate_v264.h"
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <span>
using namespace BloodborneCoop::SHYTHybrid;
namespace Stun=BloodborneCoop::SHYTHybrid::ReflexiveStunV321;
struct Udp {
    int fd=-1;
    sockaddr_in address{};
    Udp() {
        fd=::socket(AF_INET,SOCK_DGRAM,0);
        assert(fd>=0);
        address.sin_family=AF_INET;
        address.sin_port=0;
        address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        assert(::bind(fd,reinterpret_cast<const sockaddr*>(&address),
                      sizeof(address))==0);
        socklen_t size=sizeof(address);
        assert(::getsockname(fd,reinterpret_cast<sockaddr*>(&address),
                            &size)==0);
        timeval timeout{2,0};
        assert(::setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,
                            sizeof(timeout))==0);
    }
    ~Udp(){if(fd>=0)::close(fd);}
    Udp(const Udp&)=delete;
    Udp& operator=(const Udp&)=delete;
};
static Stun::Endpoint endpoint(const sockaddr_in& v) {
    return {v.sin_addr.s_addr,v.sin_port};
}
int main() {
    Udp game, stun_server;
    Stun::Binding binding;
    std::array<Stun::u8,12> txid{};
    assert(Stun::FreshTransactionIdV323(txid));
    const auto request=binding.Start(endpoint(stun_server.address),txid,1000);
    assert(request && request->size()==20);
    assert(::sendto(game.fd,request->data(),request->size(),0,
           reinterpret_cast<const sockaddr*>(&stun_server.address),
           sizeof(stun_server.address))==20);
    std::array<Stun::u8,512> request_wire{};
    sockaddr_in game_seen{};
    socklen_t size=sizeof(game_seen);
    const ssize_t received=::recvfrom(stun_server.fd,request_wire.data(),
          request_wire.size(),0,reinterpret_cast<sockaddr*>(&game_seen),&size);
    assert(received==20);
    assert(std::equal(request->begin(),request->end(),
                      request_wire.begin()));
    std::array<Stun::u8,32> response{};
    response[0]=1;response[1]=1;response[3]=12;
    std::copy(request->begin()+4,request->end(),response.begin()+4);
    response[21]=0x20;response[23]=8;response[25]=1;
    const auto* ip=reinterpret_cast<const Stun::u8*>(
        &game_seen.sin_addr.s_addr);
    const auto* port=reinterpret_cast<const Stun::u8*>(
        &game_seen.sin_port);
    for(int i=0;i<2;++i)response[26+i]=
        port[i]^Stun::Binding::Cookie[i];
    for(int i=0;i<4;++i)response[28+i]=
        ip[i]^Stun::Binding::Cookie[i];
    assert(::sendto(stun_server.fd,response.data(),response.size(),0,
           reinterpret_cast<const sockaddr*>(&game_seen),
           sizeof(game_seen))==32);
    std::array<Stun::u8,512> response_wire{};
    sockaddr_in server_seen{};
    size=sizeof(server_seen);
    const ssize_t got=::recvfrom(game.fd,response_wire.data(),
          response_wire.size(),0,reinterpret_cast<sockaddr*>(&server_seen),
          &size);
    assert(got==32 && endpoint(server_seen)==endpoint(stun_server.address));
    const auto mapped=binding.Take(endpoint(server_seen),
            std::span<const Stun::u8>{response_wire.data(),
                                      static_cast<size_t>(got)},1500);
    assert(mapped && *mapped==endpoint(game_seen));
    assert(!binding.Take(endpoint(server_seen),response,1501));
    // Even a matching STUN IP/port cannot grant original game's
    // encrypted SHDP physical route or an authenticated Noise session.
    DirectPhysicalGateV264 physical{};
    assert(!DirectPhysicalGateV264::CorrectWire(response));
    assert(!physical.Allows(
        {mapped->address_nbo,mapped->port_nbo,0},1500,response));
    std::puts("SHYT_V325_REAL_SAME_SOCKET_STUN_LOOPBACK_ADVISORY_ONLY_PASS");
}
