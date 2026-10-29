// SPDX-License-Identifier: GPL-2.0-or-later
// ORIGINAL SHY2 AES-GCM native game RX/TX components over real OS UDP sockets.
// One Alice/Bob two-way game stream plus a third simulated shadNet relay.
// This is localhost kernel UDP, NOT Internet NAT traversal and NOT a game build.
// The actual original P2PTransport's live server-grant installer is still OFF.
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
#include "sh_native_game_aead_egress.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <span>
#include <vector>
using namespace SeamlessHunt::Hybrid;
#ifdef _WIN32
using Socket = SOCKET;
static constexpr Socket Invalid = INVALID_SOCKET;
static void Close(Socket s){if(s!=Invalid)closesocket(s);}
#else
using Socket = int;
static constexpr Socket Invalid = -1;
static void Close(Socket s){if(s!=Invalid)close(s);}
#endif

class Udp final {
public:
    Udp() {
        fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
        if(fd==Invalid)return;
        sockaddr_in bindaddr{};
        bindaddr.sin_family=AF_INET;
        bindaddr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        if(bind(fd,reinterpret_cast<sockaddr*>(&bindaddr),
                sizeof(bindaddr))!=0)return;
#ifdef _WIN32
        int length=sizeof(bindaddr);
        DWORD timeout=1000;
        setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,
            reinterpret_cast<const char*>(&timeout),sizeof(timeout));
#else
        socklen_t length=sizeof(bindaddr);
        timeval timeout{};timeout.tv_sec=1;
        setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
#endif
        if(getsockname(fd,reinterpret_cast<sockaddr*>(&bindaddr),&length)==0) {
            endpoint={bindaddr.sin_addr.s_addr,bindaddr.sin_port};
        }
    }
    ~Udp(){Close(fd);}
    Udp(const Udp&)=delete;
    Udp& operator=(const Udp&)=delete;
    bool valid()const{return fd!=Invalid && endpoint.addr_nbo &&
                              endpoint.port_nbo;}
    PhysicalV4 addr()const{return endpoint;}
    bool Send(PhysicalV4 target,std::span<const std::uint8_t> wire){
        if(!valid() || !target.addr_nbo || !target.port_nbo ||
           wire.empty())return false;
        sockaddr_in dest{};
        dest.sin_family=AF_INET;dest.sin_addr.s_addr=target.addr_nbo;
        dest.sin_port=target.port_nbo;
        const auto sent=sendto(fd,reinterpret_cast<const char*>(wire.data()),
                              static_cast<int>(wire.size()),0,
                              reinterpret_cast<const sockaddr*>(&dest),
                              sizeof(dest));
        return sent==static_cast<int>(wire.size());
    }
    bool Receive(PhysicalV4& sender,std::vector<std::uint8_t>& bytes){
        bytes.clear();sender={};
        std::array<std::uint8_t,AeadDetail::MaxBytes+1> packet{};
        sockaddr_in from{};
#ifdef _WIN32
        int from_len=sizeof(from);
#else
        socklen_t from_len=sizeof(from);
#endif
        const auto count=recvfrom(fd,reinterpret_cast<char*>(packet.data()),
                                  static_cast<int>(packet.size()),0,
                                  reinterpret_cast<sockaddr*>(&from),&from_len);
        if(count<=0 || static_cast<std::size_t>(count)>AeadDetail::MaxBytes)
            return false;
        sender={from.sin_addr.s_addr,from.sin_port};
        bytes.assign(packet.begin(),packet.begin()+count);
        return true;
    }
private:
    Socket fd=Invalid;
    PhysicalV4 endpoint{};
};
struct World{bool connected=true;ChannelAuthority authority{};};
static bool Refresh(ChannelAuthority& out,void* user) noexcept {
    auto* w=static_cast<World*>(user);
    if(!w || !w->connected)return false;
    out=w->authority;return true;
}
static ChannelAuthority Allowed(){
    ChannelAuthority w{};
    w.session_grant_verified=w.both_peers_consented=w.peer_binding_verified=
      w.both_on_same_authorized_team=w.protocol_compatible=
      w.map_known=w.map_epoch_verified=w.both_on_same_map=
      w.enemy_stream_authorized=w.reliable_stream_handover_verified=true;
    w.sender_enemy_role=EnemyRole::Owner;
    w.target_enemy_role=EnemyRole::Follower;
    return w;
}
static std::array<std::uint8_t,32> Key(unsigned seed){
    std::array<std::uint8_t,32> key{};
    for(unsigned i=0;i<key.size();++i)key[i]=
       static_cast<std::uint8_t>(seed+i);
    return key;
}
static std::array<std::uint8_t,4> Salt(unsigned seed) {
    return {static_cast<std::uint8_t>(seed),
            static_cast<std::uint8_t>(seed+1),
            static_cast<std::uint8_t>(seed+2),
            static_cast<std::uint8_t>(seed+3)};
}
static PeerTicket Ticket(unsigned sender,unsigned recipient){
    PeerTicket t{};
    t.session_epoch=134;t.pair_binding=777;
    t.authenticated_sender=sender;t.local_receiver=recipient;
    t.expires_at_ms=5000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static void U32(std::vector<std::uint8_t>& x,std::uint32_t n){
    for(unsigned i=0;i<32;i+=8)x.push_back(
       static_cast<std::uint8_t>(n>>i));
}
static std::vector<std::uint8_t> Game(char sender,
                                       std::uint32_t channel=0x06,
                                       bool reliable=false,bool shared_ack=false) {
    std::vector<std::uint8_t> x{255,255,255,255,'S','H','A','D',0x40,
                                1,1,static_cast<std::uint8_t>(sender)};
    U32(x,1);U32(x,1);U32(x,shared_ack?3:0);
    x.push_back(1);x.push_back(0);
    x.push_back(reliable?1:0);
    U32(x,17);U32(x,8);U32(x,channel);U32(x,0);
    return x;
}
static NativeShy2Result ReceiveGame(
    Udp& destination,NativeGameAeadIngress& receiver,
    std::int64_t now_ms,PhysicalV4* raw_sender=nullptr) {
    PhysicalV4 from{};
    std::vector<std::uint8_t> wire;
    assert(destination.Receive(from,wire));
    if(raw_sender)*raw_sender=from;
    return receiver.Receive(from,wire,now_ms);
}
int main(){
#ifdef _WIN32
    WSADATA wsa{};
    assert(WSAStartup(MAKEWORD(2,2),&wsa)==0);
#endif
    {
        Udp alice,bob,attacker,relay;
        assert(alice.valid() && bob.valid() && attacker.valid() && relay.valid());
        assert(alice.addr().port_nbo!=bob.addr().port_nbo);
        NativeGameAeadEgress alice_tx,bob_tx;
        NativeGameAeadIngress alice_rx,bob_rx;
        World alice_world{},bob_world{};
        alice_world.authority=bob_world.authority=Allowed();
        const auto a_to_b=Ticket(11,22);
        const auto b_to_a=Ticket(22,11);
        const auto ak=Key(11);
        const auto bk=Key(91);
        const auto as=Salt(11);
        const auto bs=Salt(91);
        const VirtualV4 virtual_a{0x0100000aU,htons(20111)};
        const VirtualV4 virtual_b{0x0200000aU,htons(20222)};
        const auto a_frame=Game('A');
        const auto b_frame=Game('B');
        std::vector<std::uint8_t> wire;
        // Before a TRUSTED server grant, all game frames MUST take the
        // ORIGINAL relay path, including the whole unmodified SHAD frame.
        assert(!alice_tx.Seal(bob.addr(),a_frame,100,wire));
        assert(wire.empty());
        assert(alice.Send(relay.addr(),a_frame));
        PhysicalV4 received_from{};
        assert(relay.Receive(received_from,wire));
        assert(received_from.port_nbo==alice.addr().port_nbo &&
               wire==a_frame);
        // Runtime grant installation is intentionally not present in the
        // public game. Test only the C++ boundary AFTER a hypothetical
        // independently verified server grant, never from arbitrary UDP.
        assert(alice_tx.Arm(0,a_to_b,ak,as,bob.addr(),virtual_b,
                            "A",Refresh,&alice_world,100));
        assert(bob_rx.Arm(0,a_to_b,ak,as,alice.addr(),virtual_a,
                           "A",Refresh,&bob_world,100));
        assert(bob_tx.Arm(0,b_to_a,bk,bs,alice.addr(),virtual_a,
                          "B",Refresh,&bob_world,100));
        assert(alice_rx.Arm(0,b_to_a,bk,bs,bob.addr(),virtual_b,
                            "B",Refresh,&alice_world,100));
        assert(alice_tx.Seal(bob.addr(),a_frame,101,wire));
        assert(IsSHY2(wire) && wire.size()>a_frame.size());
        assert(alice.Send(bob.addr(),wire));
        auto result=ReceiveGame(bob,bob_rx,101,&received_from);
        assert(result.status==NativeRxStatus::Game);
        assert(result.native_game_frame==a_frame);
        assert(result.sender.addr_nbo==virtual_a.addr_nbo &&
               result.sender.port_nbo==virtual_a.port_nbo);
        assert(received_from.port_nbo==alice.addr().port_nbo);
        // Network replay, even from the ORIGINAL physical peer.
        assert(alice.Send(bob.addr(),wire));
        assert(ReceiveGame(bob,bob_rx,102).status==NativeRxStatus::Dropped);
        // Correct authenticated packet from a DIFFERENT physical endpoint
        // must never be admitted as the original player.
        assert(attacker.Send(bob.addr(),wire));
        assert(ReceiveGame(bob,bob_rx,103).status==NativeRxStatus::Dropped);
        // A malformed tag must not poison the replay window.
        assert(alice_tx.Seal(bob.addr(),a_frame,104,wire));
        auto tampered=wire;tampered.back()^=0x80;
        assert(attacker.Send(bob.addr(),tampered));
        assert(ReceiveGame(bob,bob_rx,104).status==NativeRxStatus::Dropped);
        assert(alice.Send(bob.addr(),tampered));
        assert(ReceiveGame(bob,bob_rx,104).status==NativeRxStatus::Dropped);
        assert(alice.Send(bob.addr(),wire));
        assert(ReceiveGame(bob,bob_rx,104).status==NativeRxStatus::Game);
        // Real kernel UDP B -> A uses an independent direction/key/nonce.
        assert(bob_tx.Seal(alice.addr(),b_frame,105,wire));
        assert(bob.Send(alice.addr(),wire));
        auto other=ReceiveGame(alice,alice_rx,105);
        assert(other.status==NativeRxStatus::Game &&
               other.native_game_frame==b_frame);
        assert(other.sender.addr_nbo==virtual_b.addr_nbo);
        // Reliable classes, piggybacked GameLink ACK, or server authority
        // MUST send original plaintext SHAD frame to server relay, once.
        for(const auto& non_offload: {
              Game('A',0x14,true),Game('A',0x06,false,true),
              Game('A',0x2f)}) {
            assert(!alice_tx.Seal(bob.addr(),non_offload,106,wire));
            assert(wire.empty());
            assert(alice.Send(relay.addr(),non_offload));
            assert(relay.Receive(received_from,wire));
            assert(wire==non_offload);
        }
        // Current-world/map permission revoked: no offload; normal relay.
        alice_world.authority.map_epoch_verified=false;
        assert(!alice_tx.Seal(bob.addr(),a_frame,107,wire));
        alice_world.authority.map_epoch_verified=true;
        // Receiver fresh authority also gates after valid GCM.
        bob_world.authority.map_epoch_verified=false;
        assert(alice_tx.Seal(bob.addr(),a_frame,108,wire));
        assert(alice.Send(bob.addr(),wire));
        assert(ReceiveGame(bob,bob_rx,108).status==NativeRxStatus::Dropped);
        bob_world.authority.map_epoch_verified=true;
        // Leaving team revokes the state and cannot be resurrected locally.
        bob_world.connected=false;
        assert(alice_tx.Seal(bob.addr(),a_frame,109,wire));
        assert(alice.Send(bob.addr(),wire));
        assert(ReceiveGame(bob,bob_rx,109).status==NativeRxStatus::Dropped);
        bob_world.connected=true;
        assert(alice.Send(bob.addr(),wire));
        assert(ReceiveGame(bob,bob_rx,110).status==NativeRxStatus::Dropped);
        // Expected underlying source retains no actual network read after
        // the OS kernel hands the authenticated datagram to the app.
        alice_tx.RevokeAll();
        bob_tx.RevokeAll();
        alice_rx.RevokeAll();
        bob_rx.RevokeAll();
        assert(!alice_tx.Seal(bob.addr(),a_frame,111,wire));
    }
#ifdef _WIN32
    assert(WSACleanup()==0);
#endif
    return 0;
}
