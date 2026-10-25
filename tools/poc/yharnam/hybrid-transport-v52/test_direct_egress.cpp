// SPDX-License-Identifier: GPL-2.0-or-later
// V65: A <-> B real WinSock/POSIX UDP sendto/recvfrom, real HMAC,
// authorize complete SHAD game packets or preserve old server relay.
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
#include "sh_direct_egress.hpp"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>
using namespace SeamlessHunt::Hybrid;

#ifdef _WIN32
using Socket=SOCKET;
static constexpr Socket kInvalid=INVALID_SOCKET;
static void Shut(Socket s) noexcept { if(s!=kInvalid)closesocket(s); }
#else
using Socket=int;
static constexpr Socket kInvalid=-1;
static void Shut(Socket s) noexcept { if(s!=kInvalid)close(s); }
#endif
class PeerSocket final {
public:
    PeerSocket() {
        sock_=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
        if (sock_==kInvalid) return;
        sockaddr_in addr{};
        addr.sin_family=AF_INET;
        addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        if(bind(sock_,reinterpret_cast<const sockaddr*>(&addr),sizeof(addr))!=0)
            return;
#ifdef _WIN32
        int len=sizeof(addr);DWORD timeout=1000;
        setsockopt(sock_,SOL_SOCKET,SO_RCVTIMEO,
                   reinterpret_cast<const char*>(&timeout),sizeof(timeout));
#else
        socklen_t len=sizeof(addr);
        timeval timeout{};timeout.tv_sec=1;
        setsockopt(sock_,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
#endif
        if(getsockname(sock_,reinterpret_cast<sockaddr*>(&addr),&len)==0)
            port_=ntohs(addr.sin_port);
    }
    ~PeerSocket(){Shut(sock_);}
    PeerSocket(const PeerSocket&)=delete;
    PeerSocket& operator=(const PeerSocket&)=delete;
    bool valid()const noexcept{return sock_!=kInvalid && port_!=0;}
    unsigned port()const noexcept{return port_;}
    bool Send(unsigned port,std::span<const std::uint8_t> frame)noexcept {
        if(!valid() || frame.empty())return false;
        sockaddr_in target{};
        target.sin_family=AF_INET;
        target.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        target.sin_port=htons(static_cast<std::uint16_t>(port));
        const int sent=sendto(sock_,reinterpret_cast<const char*>(frame.data()),
                              static_cast<int>(frame.size()),0,
                              reinterpret_cast<const sockaddr*>(&target),sizeof(target));
        return sent==static_cast<int>(frame.size());
    }
    bool Receive(unsigned source_port,std::vector<std::uint8_t>& out){
        std::array<std::uint8_t,DirectReceiver::kMaxDatagramBytes+1> data{};
        sockaddr_in source{};
#ifdef _WIN32
        int len=sizeof(source);
#else
        socklen_t len=sizeof(source);
#endif
        const int received=recvfrom(sock_,reinterpret_cast<char*>(data.data()),
                                    static_cast<int>(data.size()),0,
                                    reinterpret_cast<sockaddr*>(&source),&len);
        if(received<=0 || received>static_cast<int>(DirectReceiver::kMaxDatagramBytes) ||
           source.sin_addr.s_addr!=htonl(INADDR_LOOPBACK) ||
           ntohs(source.sin_port)!=source_port)
            return false;
        out.assign(data.begin(),data.begin()+received);
        return true;
    }
private:
    Socket sock_=kInvalid;
    unsigned port_=0;
};
struct DirectIo { PeerSocket* socket=nullptr;unsigned target=0;bool fail=false; };
static bool SendDirect(std::span<const std::uint8_t> frame,void* ctx)noexcept {
    auto& io=*static_cast<DirectIo*>(ctx);
    return !io.fail && io.socket && io.socket->Send(io.target,frame);
}
struct RelayCapture {std::vector<std::uint8_t> packet;unsigned count=0;bool fail=false;};
static bool SendRelay(std::span<const std::uint8_t> frame,void* ctx)noexcept {
    auto& out=*static_cast<RelayCapture*>(ctx);
    if(out.fail)return false;
    out.packet.assign(frame.begin(),frame.end());
    ++out.count;
    return true;
}
static void U32(std::vector<std::uint8_t>& data,std::uint32_t value){
    for(unsigned k=0;k<32;k+=8)data.push_back(static_cast<std::uint8_t>(value>>k));
}
static std::vector<std::uint8_t> NativeGame(std::uint32_t channel,
                                             std::string_view sender,
                                             std::size_t data_size=0){
    assert(sender.size()==1);
    std::vector<std::uint8_t> p{255,255,255,255,'S','H','A','D',0x40,1,1,
                                static_cast<std::uint8_t>(sender[0])};
    U32(p,1);U32(p,1);U32(p,0);
    p.push_back(1);p.push_back(0); // one native game packet
    p.push_back(static_cast<std::uint8_t>(channel>6?1:0));
    U32(p,17);U32(p,static_cast<std::uint32_t>(8+data_size));
    U32(p,channel);U32(p,static_cast<std::uint32_t>(data_size));
    p.insert(p.end(),data_size,0x29);
    return p;
}
static PeerTicket Ticket(std::uint64_t sender,std::uint64_t receiver) {
    PeerTicket t{};
    t.session_epoch=775;t.pair_binding=997;
    t.authenticated_sender=sender;t.local_receiver=receiver;
    t.expires_at_ms=20000;
    t.server_grant_verified=t.both_consented=t.version_compatible=true;
    return t;
}
static Grant GrantFor(const PeerTicket& t) {
    Grant g{};
    g.session_epoch=t.session_epoch;g.peer_binding=t.pair_binding;
    g.valid_until_ms=t.expires_at_ms;
    g.verified_server_authorization=g.local_consent=g.peer_consent=
        g.protocol_compatible=true;
    return g;
}
static ChannelAuthority Authorized() {
    ChannelAuthority a{};
    a.session_grant_verified=a.both_peers_consented=a.peer_binding_verified=
        a.both_on_same_authorized_team=a.protocol_compatible=
        a.map_known=a.map_epoch_verified=a.both_on_same_map=
        a.enemy_stream_authorized=a.reliable_stream_handover_verified=true;
    a.sender_enemy_role=EnemyRole::Owner;
    a.target_enemy_role=EnemyRole::Follower;
    return a;
}
static std::array<std::uint8_t,32> Key(std::uint8_t seed){
    std::array<std::uint8_t,32> result{};
    for(unsigned i=0;i<32;++i)
        result[i]=static_cast<std::uint8_t>(seed+i);
    return result;
}
int main(){
#ifdef _WIN32
    WSADATA wsa{};
    assert(WSAStartup(MAKEWORD(2,2),&wsa)==0);
#endif
    {
        PeerSocket asock,bsock;
        assert(asock.valid() && bsock.valid() && asock.port()!=bsock.port());
        DirectIo aio{&asock,bsock.port(),false};
        DirectIo bio{&bsock,asock.port(),false};
        RelayCapture relay{};
        const auto aout=Ticket(11,22);
        const auto bout=Ticket(22,11);
        DirectionMac amac,bmac;
        assert(amac.InstallKey(Key(1)));
        assert(bmac.InstallKey(Key(45)));
        DirectIngress ain,bin;
        assert(ain.Arm(bout,GrantFor(bout),"B",100));
        assert(bin.Arm(aout,GrantFor(aout),"A",100));
        assert(ain.MatchesReverse(aout));
        assert(bin.MatchesReverse(bout));
        auto corrupt=aout;corrupt.pair_binding+=1;
        assert(!ain.MatchesReverse(corrupt));
        corrupt=aout;corrupt.session_epoch+=1;
        assert(!ain.MatchesReverse(corrupt));
        corrupt=aout;corrupt.local_receiver=11;
        assert(!ain.MatchesReverse(corrupt));
        DirectEgress a,b;
        assert(!a.Arm(corrupt,amac,ain,100));
        assert(a.Arm(aout,amac,ain,100));
        assert(b.Arm(bout,bmac,bin,100));
        assert(ain.CurrentPath(100)==Path::Relay);
        const auto valid=NativeGame(0x06,"A");
        const auto world=Authorized();
        // Before reverse-path probes, unchanged original frames use shadNet.
        assert(a.SendGame(valid,"A",world,102,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        assert(relay.packet==valid);
        assert(a.stats().direct_frames==0);
        assert(relay.count==1);
        std::vector<std::uint8_t> frame;
        std::span<const std::uint8_t> game{};
        // Both directions must verify their own independently keyed probes.
        for(int i=0;i<3;++i) {
            const auto now=110+i;
            assert(a.SendControl(DirectKind::Probe,now,SendDirect,&aio));
            assert(bsock.Receive(asock.port(),frame));
            assert(bin.Receive(frame,now,DirectionMac::VerifyCallback,
                     &amac,world,game)==IngressStatus::AuthenticatedProbeOrHeartbeat);
            assert(b.SendControl(DirectKind::Probe,now,SendDirect,&bio));
            assert(asock.Receive(bsock.port(),frame));
            assert(ain.Receive(frame,now,DirectionMac::VerifyCallback,
                     &bmac,world,game)==IngressStatus::AuthenticatedProbeOrHeartbeat);
        }
        assert(ain.CurrentPath(120)==Path::Direct);
        assert(bin.CurrentPath(120)==Path::Direct);
        assert(a.SendGame(valid,"A",world,120,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::DirectSent);
        assert(bsock.Receive(asock.port(),frame));
        assert(frame.size()>valid.size());
        assert(bin.Receive(frame,120,DirectionMac::VerifyCallback,
               &amac,world,game)==IngressStatus::AuthenticatedGame);
        assert(game.size()==valid.size());
        assert(std::equal(game.begin(),game.end(),valid.begin()));
        assert(!bin.Receive(frame,120,DirectionMac::VerifyCallback,
                &amac,world,game)); // replay blocked
        assert(a.stats().direct_frames==1 && a.stats().relay_frames==1);
        assert(relay.count==1); // no duplicate server forwarding
        // Spoofed inner sender, map epoch, unsafe owner and native server
        // authority must always retain ORIGINAL reliable/unreliable frame.
        assert(a.SendGame(valid,"B",world,125,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        const auto server_owned=NativeGame(0x2f,"A");
        assert(a.SendGame(server_owned,"A",world,126,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        auto stale=world;stale.map_epoch_verified=false;
        assert(a.SendGame(valid,"A",stale,127,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        const auto reliable=NativeGame(0x14,"A");
        auto unmigrated=world;unmigrated.reliable_stream_handover_verified=false;
        assert(a.SendGame(reliable,"A",unmigrated,128,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        const auto too_large=NativeGame(0x06,"A",DirectReceiver::kMaxPayloadBytes);
        assert(too_large.size()>DirectReceiver::kMaxPayloadBytes);
        assert(a.SendGame(too_large,"A",world,129,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        assert(relay.packet==too_large);
        // A syscall-level direct failure forces cooldown and SAME native game
        // frame back to relay, and prevents retry thrashing.
        aio.fail=true;
        assert(a.SendGame(valid,"A",world,130,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        assert(relay.packet==valid);
        assert(a.stats().direct_failures==1);
        assert(ain.CurrentPath(131)==Path::Relay);
        aio.fail=false;
        assert(a.SendGame(valid,"A",world,132,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        assert(a.stats().direct_failures==1); // no repeated direct attempts
        // Server fallback failure is visible, never reported as delivered.
        relay.fail=true;
        assert(a.SendGame(valid,"A",world,133,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::BothFailed);
        // Once expired, no authenticated direct retry is possible.
        relay.fail=false;
        assert(a.SendGame(valid,"A",world,20001,SendDirect,&aio,SendRelay,&relay)
               ==GameSendResult::RelaySent);
        a.Reset();
        assert(a.stats().direct_frames==0);
        assert(a.stats().relay_frames==0);
    }
#ifdef _WIN32
    assert(WSACleanup()==0);
#endif
    return 0;
}
