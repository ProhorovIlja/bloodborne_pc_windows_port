// SPDX-License-Identifier: GPL-2.0-or-later
// V91 real OS kernel UDP loopback proof between two ephemeral test sockets.
// Does NOT replace or access Bloodborne's actual running game UDP socket.
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
#include "sh_nat_probe_v91.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using namespace SeamlessHunt::Hybrid;
#ifdef _WIN32
using Fd=SOCKET;
static constexpr Fd invalid_fd=INVALID_SOCKET;
static void Close(Fd x){if(x!=invalid_fd)closesocket(x);}
#else
using Fd=int;
static constexpr Fd invalid_fd=-1;
static void Close(Fd x){if(x!=invalid_fd)close(x);}
#endif
struct LoopSocket{
    Fd fd=invalid_fd;
    std::uint16_t port_nbo=0;
    LoopSocket(){
        fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
        assert(fd!=invalid_fd);
        sockaddr_in addr{};
        addr.sin_family=AF_INET;
        addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        addr.sin_port=0;
        assert(bind(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))==0);
#ifdef _WIN32
        DWORD limit=2000;int len=sizeof(addr);
        assert(setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,
                          reinterpret_cast<const char*>(&limit),sizeof(limit))==0);
#else
        timeval limit{2,0};socklen_t len=sizeof(addr);
        assert(setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&limit,sizeof(limit))==0);
#endif
        assert(getsockname(fd,reinterpret_cast<sockaddr*>(&addr),&len)==0);
        port_nbo=addr.sin_port;
        assert(port_nbo!=0);
    }
    ~LoopSocket(){Close(fd);}
    LoopSocket(const LoopSocket&)=delete;
    LoopSocket& operator=(const LoopSocket&)=delete;
    void Send(const NatProbeCodecV91::Wire& data,std::uint16_t dst) {
        sockaddr_in to{};
        to.sin_family=AF_INET;to.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        to.sin_port=dst;
        assert(sendto(fd,reinterpret_cast<const char*>(data.data()),
                      static_cast<int>(data.size()),0,
                      reinterpret_cast<const sockaddr*>(&to),sizeof(to))==
                      static_cast<int>(data.size()));
    }
    NatProbeCodecV91::Wire Read(std::uint16_t source_port){
        NatProbeCodecV91::Wire wire{};
        sockaddr_in from{};
#ifdef _WIN32
        int len=sizeof(from);
#else
        socklen_t len=sizeof(from);
#endif
        const int count=recvfrom(fd,reinterpret_cast<char*>(wire.data()),
              static_cast<int>(wire.size()),0,
              reinterpret_cast<sockaddr*>(&from),&len);
        assert(count==static_cast<int>(wire.size()));
        assert(from.sin_family==AF_INET);
        assert(from.sin_port==source_port);
        assert(from.sin_addr.s_addr==htonl(INADDR_LOOPBACK));
        return wire;
    }
};
static std::array<std::uint8_t,32> Id(unsigned salt){
    std::array<std::uint8_t,32> id{};
    for(unsigned i=0;i<id.size();++i)
        id[i]=static_cast<std::uint8_t>(salt+i);
    return id;
}
static SecurePeerOfferV84 Grant(const std::array<std::uint8_t,32>& self,
                               const std::array<std::uint8_t,32>& peer,
                               std::uint16_t peer_port){
    SecurePeerOfferV84 g{};
    g.recipient_account=self;g.sender_account=peer;
    g.session_epoch=self[0];
    g.pair_binding=9001;g.world_revision=2300;
    g.issued_ms=1000;g.expires_ms=2000;
    g.peer_ipv4_nbo=htonl(INADDR_LOOPBACK);
    g.peer_port_nbo=peer_port;
    g.peer_virtual_ipv4_nbo=htonl(0x0a000001U);
    g.peer_virtual_port_nbo=htons(31314);
    g.direction_key=Id(100);
    return g;
}
int main(){
#ifdef _WIN32
    WSADATA wsa{};
    assert(WSAStartup(MAKEWORD(2,2),&wsa)==0);
#endif
    {
        LoopSocket a,b;
        assert(a.port_nbo!=b.port_nbo);
        auto alice=Grant(Id(7),Id(31),b.port_nbo);
        auto bob=Grant(Id(31),Id(7),a.port_nbo);
        NatProbeProofV91 initiator(NatProbeProofV91::Role::Initiator);
        NatProbeProofV91 responder(NatProbeProofV91::Role::Responder);
        assert(initiator.Start(alice,1000));
        assert(responder.Start(bob,1000));
        NatProbeCodecV91::Wire packet{},answer{};
        assert(initiator.Initial(1001,packet));
        assert(!initiator.Initial(1002,answer)); // cannot initiate twice
        a.Send(packet,b.port_nbo);
        const auto wire_challenge=b.Read(a.port_nbo);
        // Wrong socket source, stale world, wrong master, tampered auth
        // must be rejected before replay state is updated.
        auto changed=wire_challenge;changed[115]^=1;
        assert(!responder.Reply(changed,htonl(INADDR_LOOPBACK),a.port_nbo,
                                1002,answer));
        assert(!responder.Reply(wire_challenge,htonl(INADDR_LOOPBACK),
                                htons(10000),1002,answer));
        assert(!responder.Reply(wire_challenge,htonl(INADDR_LOOPBACK),
                                a.port_nbo,2000,answer));
        assert(responder.Reply(wire_challenge,htonl(INADDR_LOOPBACK),
                               a.port_nbo,1002,answer));
        // The identical verified nonce+seq cannot be consumed again.
        assert(!responder.Reply(wire_challenge,htonl(INADDR_LOOPBACK),
                                a.port_nbo,1002,packet));
        b.Send(answer,a.port_nbo);
        auto wire_response=a.Read(b.port_nbo);
        assert(initiator.Reply(wire_response,htonl(INADDR_LOOPBACK),
                               b.port_nbo,1003,packet));
        a.Send(packet,b.port_nbo);
        auto wire_confirm=b.Read(a.port_nbo);
        assert(responder.Reply(wire_confirm,htonl(INADDR_LOOPBACK),
                               a.port_nbo,1004,answer));
        b.Send(answer,a.port_nbo);
        const auto wire_ready=a.Read(b.port_nbo);
        assert(!initiator.InitiatorVerified());
        assert(!responder.ResponderVerified());
        NatProbeCodecV91::Wire receipt{};
        assert(initiator.Complete(wire_ready,htonl(INADDR_LOOPBACK),
                                  b.port_nbo,1005,receipt));
        assert(!initiator.InitiatorVerified()); // send not reported yet
        assert(!initiator.Complete(wire_ready,htonl(INADDR_LOOPBACK),
                                   b.port_nbo,1006,packet)); // replay
        assert(!initiator.ReceiptSent(wire_ready)); // wrong wire
        assert(!responder.CompleteResponder(wire_ready,
                    htonl(INADDR_LOOPBACK),a.port_nbo,1005));
        auto forged=receipt;forged[143]^=1;
        assert(!responder.CompleteResponder(forged,
                    htonl(INADDR_LOOPBACK),a.port_nbo,1005));
        assert(!responder.CompleteResponder(receipt,
                    htonl(INADDR_LOOPBACK),htons(10000),1005));
        a.Send(receipt,b.port_nbo);
        assert(initiator.ReceiptSent(receipt));
        assert(initiator.InitiatorVerified());
        assert(!initiator.ReceiptSent(receipt));
        const auto wire_receipt=b.Read(a.port_nbo);
        assert(responder.CompleteResponder(wire_receipt,
                    htonl(INADDR_LOOPBACK),a.port_nbo,1006));
        assert(responder.ResponderVerified());
        assert(!responder.CompleteResponder(wire_receipt,
                    htonl(INADDR_LOOPBACK),a.port_nbo,1007));
        // A completed *proof* is NOT game routing permission.
        std::array<std::uint8_t,32> a_tx{},b_rx{},game{};
        assert(PairKeyScheduleV89::Derive(alice,true,PairKeyPurposeV89::NatProbe,
                                         1005,a_tx));
        assert(PairKeyScheduleV89::Derive(bob,false,PairKeyPurposeV89::NatProbe,
                                         1005,b_rx));
        assert(PairKeyScheduleV89::Derive(alice,true,PairKeyPurposeV89::GameData,
                                         1005,game));
        assert(a_tx==b_rx && game!=a_tx);
        CryptoDetail::Erase(a_tx);CryptoDetail::Erase(b_rx);
        CryptoDetail::Erase(game);
        initiator.Reset();responder.Reset();
        assert(!initiator.InitiatorVerified());
        assert(!responder.ResponderVerified());

        // Strict identity/pair/world/endpoint checks with REAL HMAC.
        NatProbeCodecV91::Wire good{};
        NatProbeFrameV91 f{};
        f.kind=NatProbeKindV91::Challenge;f.seq=1;
        assert(NatProbeCodecV91::FreshNonce(f.nonce));
        assert(NatProbeCodecV91::Encode(alice,f,1100,good));
        NatProbeCodecV91::Receiver incoming;
        NatProbeFrameV91 opened{};
        assert(!incoming.Open(bob,0,a.port_nbo,good,1100,opened));
        assert(!incoming.Open(bob,htonl(INADDR_LOOPBACK),htons(31415),
                              good,1100,opened));
        auto different=bob;different.pair_binding++;
        assert(!incoming.Open(different,htonl(INADDR_LOOPBACK),a.port_nbo,
                              good,1100,opened));
        different=bob;different.world_revision++;
        assert(!incoming.Open(different,htonl(INADDR_LOOPBACK),a.port_nbo,
                              good,1100,opened));
        different=bob;different.direction_key[31]^=1;
        assert(!incoming.Open(different,htonl(INADDR_LOOPBACK),a.port_nbo,
                              good,1100,opened));
        for(std::size_t index : {std::size_t(0),std::size_t(4),
             std::size_t(24),std::size_t(56),std::size_t(96),
             std::size_t(127),std::size_t(143)}) {
            auto corrupt=good;corrupt[index]^=1;
            assert(!incoming.Open(bob,htonl(INADDR_LOOPBACK),a.port_nbo,
                                  corrupt,1100,opened));
        }
        assert(incoming.Open(bob,htonl(INADDR_LOOPBACK),a.port_nbo,
                             good,1100,opened));
        assert(opened.kind==NatProbeKindV91::Challenge);
        assert(!incoming.Open(bob,htonl(INADDR_LOOPBACK),a.port_nbo,
                              good,1100,opened));
        f.seq=2;f.kind=NatProbeKindV91::Response;f.echo.fill(0);
        assert(!NatProbeCodecV91::Encode(alice,f,1101,packet));
        assert((packet==NatProbeCodecV91::Wire{}));
        f.kind=NatProbeKindV91::Challenge;f.seq=0;
        assert(!NatProbeCodecV91::Encode(alice,f,1101,packet));
    }
#ifdef _WIN32
    assert(WSACleanup()==0);
#endif
    return 0;
}
