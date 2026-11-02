// SPDX-License-Identifier: GPL-2.0-or-later
// V327: actual kernel UDP 3-message original YT Noise NK connectivity
// against exact server-signed endpoint and authenticated AEAD finish.
// This proves local reachability, NOT Internet NAT punching or game boot.
#include "yt_signed_connectivity_v327.h"
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;
namespace Proof=BloodborneCoop::SHYTHybrid::ConnectivityV327;
namespace Grant=BloodborneCoop::SHYTHybrid::SignedPeerGrantV279;
struct Udp {
    int fd=-1;
    sockaddr_in addr{};
    Udp(){
        fd=::socket(AF_INET,SOCK_DGRAM,0);
        assert(fd>=0);
        addr.sin_family=AF_INET;
        addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
        assert(::bind(fd,reinterpret_cast<const sockaddr*>(&addr),sizeof(addr))==0);
        socklen_t n=sizeof(addr);
        assert(::getsockname(fd,reinterpret_cast<sockaddr*>(&addr),&n)==0);
        timeval timeout{2,0};
        assert(::setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))==0);
    }
    Udp(const Udp&)=delete;
    Udp& operator=(const Udp&)=delete;
    ~Udp(){if(fd>=0)::close(fd);}
    void Send(const Udp& dest,const std::vector<u8>& bytes)const {
        assert(!bytes.empty() && bytes.size()<=1200);
        assert(::sendto(fd,bytes.data(),bytes.size(),0,
            reinterpret_cast<const sockaddr*>(&dest.addr),sizeof(dest.addr))==
            static_cast<ssize_t>(bytes.size()));
    }
    struct Frame {
        std::vector<u8> bytes;
        Proof::Endpoint from;
    };
    Frame Recv()const {
        std::array<u8,1400> buf{};
        sockaddr_in from{};
        socklen_t n=sizeof(from);
        const ssize_t count=::recvfrom(fd,buf.data(),buf.size(),0,
            reinterpret_cast<sockaddr*>(&from),&n);
        assert(count>0 && count<=1200);
        return {{buf.begin(),buf.begin()+count},
                {from.sin_addr.s_addr,from.sin_port}};
    }
    Proof::Endpoint Endpoint()const {
        return {addr.sin_addr.s_addr,addr.sin_port};
    }
};
static LinkAuth::Key Secret(u8 start) {
    LinkAuth::Key v{};
    for(std::size_t i=0;i<v.size();++i)
        v[i]=static_cast<u8>(start+i);
    return v;
}
int main(){
    Udp a,b,attacker;
    const auto scope=PeerCryptoScopeV241{"world:42","A","B",17,29,42,0x101};
    Grant::PubKey pub{};
    Grant::SecretKey key{};
    std::array<u8,32> seed{};
    for(std::size_t i=0;i<seed.size();++i)
        seed[i]=static_cast<u8>(i+37);
    LinkMonocypher::crypto_eddsa_key_pair(key.data(),pub.data(),seed.data());
    const auto responder_secret=Secret(45);
    const auto responder_pub=LinkAuth::Noise::PublicOf(responder_secret);
    const s64 unix_now=1810000000000LL;
    Grant::Scope request{};
    request.team="five-hunters";
    request.party="world:42";
    request.sender="A";request.receiver="B";
    request.sender_instance=17;request.receiver_instance=29;
    request.map=0x101;request.world_epoch=42;
    request.issued_unix_ms=unix_now;
    request.expires_unix_ms=unix_now+10000;
    request.sender_ip_nbo=a.Endpoint().address_nbo;
    request.sender_port_nbo=a.Endpoint().port_nbo;
    request.receiver_ip_nbo=b.Endpoint().address_nbo;
    request.receiver_port_nbo=b.Endpoint().port_nbo;
    request.responder_noise_pub=responder_pub;
    for(std::size_t i=0;i<request.grant_nonce.size();++i)
        request.grant_nonce[i]=static_cast<u8>(i+51);
    const auto signed_pair=Grant::Sign(request,key);
    assert(signed_pair);
    const Grant::Expect view{"five-hunters","world:42","A","B",17,29,0x101,42};
    Proof::Initiator initiator(scope,*signed_pair,pub,view);
    Proof::Responder responder(scope,*signed_pair,pub,view,responder_secret);
    assert(!initiator.ReadyForDirect() && !responder.ReadyForDirect());
    const auto hello=initiator.Start(Secret(71),unix_now,1000);
    assert(hello && hello->size()==PeerNoiseV244::WireBytes);
    assert(!initiator.Start(Secret(73),unix_now,1001));
    attacker.Send(b,*hello);
    auto frame=b.Recv();
    assert(!responder.OnHello(frame.from,frame.bytes,Secret(111),unix_now+1,1001));
    a.Send(b,*hello);
    frame=b.Recv();
    const auto answer=responder.OnHello(
        frame.from,frame.bytes,Secret(115),unix_now+2,1002);
    assert(answer && !responder.ReadyForDirect());
    attacker.Send(a,*answer);
    auto forged_source=a.Recv();
    assert(!initiator.OnAnswer(forged_source.from,forged_source.bytes,
                              unix_now+3,1003));
    auto forged_answer=*answer;
    forged_answer.back()^=0x40;
    b.Send(a,forged_answer);
    auto forged_crypto=a.Recv();
    assert(!initiator.OnAnswer(forged_crypto.from,forged_crypto.bytes,
                              unix_now+4,1004));
    b.Send(a,*answer);
    frame=a.Recv();
    const auto ready=initiator.OnAnswer(frame.from,frame.bytes,
                                        unix_now+5,1005);
    assert(ready && ready->confirm.size()==Proof::ConfirmWireBytes);
    assert(initiator.ReadyForDirect() && !responder.ReadyForDirect());
    attacker.Send(b,ready->confirm);
    frame=b.Recv();
    assert(!responder.OnFinish(frame.from,frame.bytes,unix_now+6,1006));
    auto forged_confirm=ready->confirm;
    forged_confirm.back()^=0x01;
    a.Send(b,forged_confirm);
    frame=b.Recv();
    assert(!responder.OnFinish(frame.from,frame.bytes,unix_now+7,1007));
    a.Send(b,ready->confirm);
    frame=b.Recv();
    assert(responder.OnFinish(frame.from,frame.bytes,unix_now+8,1008));
    assert(responder.ReadyForDirect());
    assert(!responder.OnFinish(frame.from,frame.bytes,unix_now+9,1009));

    // Bad pin, expired signed grant and stale steady clock must deny.
    auto wrong_pub=pub;wrong_pub[0]^=1;
    Proof::Initiator untrusted(scope,*signed_pair,wrong_pub,view);
    assert(!untrusted.Start(Secret(87),unix_now,1000));
    Proof::Initiator too_late(scope,*signed_pair,pub,view);
    assert(!too_late.Start(Secret(89),unix_now+10000,1000));
    Proof::Initiator no_reply(scope,*signed_pair,pub,view);
    const auto lost=no_reply.Start(Secret(91),unix_now,1000);
    assert(lost && !no_reply.OnAnswer(
        b.Endpoint(),*answer,unix_now+3000,3501));
    no_reply.Reset();
    assert(!no_reply.ReadyForDirect());

    std::puts("SHYT_V327_REAL_UDP_SIGNED_NOISE_THREE_WAY_CONNECTIVITY_PASS");
}
