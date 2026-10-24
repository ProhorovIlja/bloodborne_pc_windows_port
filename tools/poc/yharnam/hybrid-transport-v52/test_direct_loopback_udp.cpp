// SPDX-License-Identifier: GPL-2.0-or-later
// V61: ACTUAL local kernel UDP sendto/recvfrom test of authenticated SHAD
// game frames. Loopback ONLY, no production sockets, NAT/STUN or player data.
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#endif
#include "sh_direct_crypto.hpp"
#include "sh_direct_ingress.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <span>
#include <vector>
using namespace SeamlessHunt::Hybrid;

#ifdef _WIN32
using NativeSocket=SOCKET;
constexpr NativeSocket kInvalid=INVALID_SOCKET;
static void Close(NativeSocket sock) { if(sock!=kInvalid)closesocket(sock); }
#else
using NativeSocket=int;
constexpr NativeSocket kInvalid=-1;
static void Close(NativeSocket sock) { if(sock!=kInvalid)close(sock); }
#endif
class LoopbackSocket {
public:
    LoopbackSocket() {
        socket_=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
        if(socket_==kInvalid)return;
        sockaddr_in bindaddr{};
        bindaddr.sin_family=AF_INET;
        bindaddr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        bindaddr.sin_port=0;
        if(bind(socket_,reinterpret_cast<const sockaddr*>(&bindaddr),
                sizeof(bindaddr))!=0){Close(socket_);socket_=kInvalid;return;}
        sockaddr_in where{};
#ifdef _WIN32
        int len=sizeof(where);
        DWORD ms=2000;
        setsockopt(socket_,SOL_SOCKET,SO_RCVTIMEO,
                   reinterpret_cast<const char*>(&ms),sizeof(ms));
#else
        socklen_t len=sizeof(where);
        timeval limit{};limit.tv_sec=2;
        setsockopt(socket_,SOL_SOCKET,SO_RCVTIMEO,&limit,sizeof(limit));
#endif
        if(getsockname(socket_,reinterpret_cast<sockaddr*>(&where),&len)!=0){
            Close(socket_);socket_=kInvalid;return;
        }
        port_=ntohs(where.sin_port);
    }
    ~LoopbackSocket(){Close(socket_);}
    LoopbackSocket(const LoopbackSocket&)=delete;
    LoopbackSocket& operator=(const LoopbackSocket&)=delete;
    bool valid()const{return socket_!=kInvalid && port_!=0;}
    unsigned port()const{return port_;}
    bool Send(unsigned destination,std::span<const std::uint8_t> data){
        sockaddr_in peer{};
        peer.sin_family=AF_INET;
        peer.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        peer.sin_port=htons(static_cast<std::uint16_t>(destination));
        const auto sent=sendto(socket_,reinterpret_cast<const char*>(data.data()),
                               static_cast<int>(data.size()),0,
                               reinterpret_cast<sockaddr*>(&peer),sizeof(peer));
        return sent==static_cast<int>(data.size());
    }
    bool Receive(std::vector<std::uint8_t>& data,unsigned expected_source){
        std::array<std::uint8_t,DirectReceiver::kMaxDatagramBytes+1> buffer{};
        sockaddr_in source{};
#ifdef _WIN32
        int addr_len=sizeof(source);
#else
        socklen_t addr_len=sizeof(source);
#endif
        const int n=recvfrom(socket_,reinterpret_cast<char*>(buffer.data()),
                             static_cast<int>(buffer.size()),0,
                             reinterpret_cast<sockaddr*>(&source),&addr_len);
        if(n<=0 || n>static_cast<int>(DirectReceiver::kMaxDatagramBytes) ||
           source.sin_addr.s_addr!=htonl(INADDR_LOOPBACK) ||
           ntohs(source.sin_port)!=expected_source)
            return false;
        data.assign(buffer.begin(),buffer.begin()+n);
        return true;
    }
private:
    NativeSocket socket_=kInvalid;
    unsigned port_=0;
};
static void U32(std::vector<std::uint8_t>& b,std::uint32_t v) {
    for(unsigned i=0;i<32;i+=8)
        b.push_back(static_cast<std::uint8_t>(v>>i));
}
static void U16(std::vector<std::uint8_t>& b,std::uint16_t v) {
    b.push_back(static_cast<std::uint8_t>(v));
    b.push_back(static_cast<std::uint8_t>(v>>8));
}
static std::vector<std::uint8_t> NativeGame(std::uint32_t channel){
    std::vector<std::uint8_t> b{255,255,255,255,'S','H','A','D',0x40,1,1,'X'};
    U32(b,1);U32(b,1);U32(b,0);U16(b,1);
    b.push_back(channel>6?1:0);U32(b,11);U32(b,8);
    U32(b,channel);U32(b,0);
    return b;
}
static PeerTicket Ticket(){
    PeerTicket p{};
    p.session_epoch=66;p.pair_binding=77;
    p.authenticated_sender=101;p.local_receiver=202;
    p.expires_at_ms=20000;
    p.server_grant_verified=p.both_consented=p.version_compatible=true;
    return p;
}
static Grant GrantFor(const PeerTicket& t){
    Grant g{};
    g.session_epoch=t.session_epoch;g.peer_binding=t.pair_binding;
    g.valid_until_ms=t.expires_at_ms;
    g.verified_server_authorization=g.local_consent=g.peer_consent=
        g.protocol_compatible=true;
    return g;
}
static ChannelAuthority World(){
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=a.peer_binding_verified=
        a.both_on_same_authorized_team=a.protocol_compatible=
        a.map_known=a.map_epoch_verified=a.both_on_same_map=
        a.enemy_stream_authorized=a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;
    return a;
}
int main(){
#ifdef _WIN32
    WSADATA wsa{};
    assert(WSAStartup(MAKEWORD(2,2),&wsa)==0);
#endif
    {
        LoopbackSocket clientA,clientB;
        assert(clientA.valid() && clientB.valid());
        assert(clientA.port()!=clientB.port());
        std::array<std::uint8_t,32> secret{};
        for(unsigned i=0;i<secret.size();++i)
            secret[i]=static_cast<std::uint8_t>(i+1);
        DirectionMac send_mac, recv_mac;
        assert(send_mac.InstallKey(secret));
        assert(recv_mac.InstallKey(secret));
        DirectEncoder sender;
        DirectIngress receiver;
        const auto t=Ticket();
        assert(sender.Arm(t,send_mac,100));
        assert(receiver.Arm(t,GrantFor(t),"X",100));
        const auto world=World();
        std::vector<std::uint8_t> wire, read;
        std::span<const std::uint8_t> game{};
        for(int i=0;i<3;++i){
            const auto now=110+i;
            assert(sender.Encode(DirectKind::Probe,{},now,wire));
            assert(clientA.Send(clientB.port(),wire));
            assert(clientB.Receive(read,clientA.port()));
            assert(receiver.Receive(read,now,DirectionMac::VerifyCallback,
                       &recv_mac,world,game)==IngressStatus::AuthenticatedProbeOrHeartbeat);
        }
        assert(receiver.CurrentPath(120)==Path::Direct);
        const auto payload=NativeGame(0x06);
        assert(sender.Encode(DirectKind::GameData,payload,120,wire));
        auto bad=wire;bad[DirectReceiver::kHeaderBytes]^=1;
        assert(clientA.Send(clientB.port(),bad));
        assert(clientB.Receive(read,clientA.port()));
        assert(receiver.Receive(read,120,DirectionMac::VerifyCallback,
                   &recv_mac,world,game)==IngressStatus::Reject);
        assert(game.empty());
        assert(clientA.Send(clientB.port(),wire));
        assert(clientB.Receive(read,clientA.port()));
        assert(receiver.Receive(read,121,DirectionMac::VerifyCallback,
                   &recv_mac,world,game)==IngressStatus::AuthenticatedGame);
        assert(game.size()==payload.size());
        assert(game[8]==0x40);
        assert(receiver.CurrentPath(2112)==Path::Relay); // no verified heartbeat
        assert(sender.Encode(DirectKind::GameData,NativeGame(0x06),2113,wire));
        assert(clientA.Send(clientB.port(),wire));
        assert(clientB.Receive(read,clientA.port()));
        assert(receiver.Receive(read,2113,DirectionMac::VerifyCallback,
                   &recv_mac,world,game)==IngressStatus::Reject);
        assert(game.empty()); // caller must use relay
    }
#ifdef _WIN32
    assert(WSACleanup()==0);
#endif
    return 0;
}
