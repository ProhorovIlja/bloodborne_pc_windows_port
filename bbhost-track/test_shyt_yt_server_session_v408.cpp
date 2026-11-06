// SPDX-License-Identifier: GPL-2.0-or-later
// Real V408 BBHost session controller against ORIGINAL YT server Responder,
// with ACTUAL localhost OS UDP sockets. Invented identity, build, secret,
// game messages and fixed TEST keys. Never Fornex, retail or live accounts.
#include "shyt_yt_server_session_v408.h"
#include "core/libraries/network/net_link.h"
#include "coop/link_auth.h"
#include "coop/coop_stream.h"
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
using test_fd=SOCKET;
using test_len=int;
static constexpr test_fd invalid_fd=INVALID_SOCKET;
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
using test_fd=int;
using test_len=socklen_t;
static constexpr test_fd invalid_fd=-1;
#endif
namespace YT=Libraries::Net::Link;
static int bad(unsigned n) {
    std::fprintf(stderr,"SHYT_V408_LOCAL_AUTHENTICATED_CONTROLLER_CASE_%u_FAILED\n",n);
    return static_cast<int>(n);
}
static std::array<u8,32> fake_key(unsigned v) {
    std::array<u8,32> k{};
    for(size_t i=0;i<k.size();++i)k[i]=static_cast<u8>(v+i*5u);
    return k;
}
static void close_raw(test_fd fd) {
#ifdef _WIN32
    closesocket(fd);
#else
    close(fd);
#endif
}
static std::vector<u8> receive(test_fd fd,sockaddr_in& from) {
    std::array<u8,2048> packet{};
    test_len fromlen=sizeof(from);
    const int n=recvfrom(fd,reinterpret_cast<char*>(packet.data()),
                         static_cast<int>(packet.size()),0,
                         reinterpret_cast<sockaddr*>(&from),&fromlen);
    return n>0?std::vector<u8>(packet.begin(),packet.begin()+n):
               std::vector<u8>{};
}
static bool send_to(test_fd fd,const sockaddr_in& to,const std::vector<u8>& p) {
    return sendto(fd,reinterpret_cast<const char*>(p.data()),
                  static_cast<int>(p.size()),0,
                  reinterpret_cast<const sockaddr*>(&to),sizeof(to))==
           static_cast<int>(p.size());
}
int main() {
#ifdef _WIN32
    WSADATA ws{};
    if(WSAStartup(MAKEWORD(2,2),&ws)!=0)return bad(1);
#endif
    const test_fd server=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(server==invalid_fd)return bad(2);
#ifdef _WIN32
    DWORD timeout=1500;
    if(setsockopt(server,SOL_SOCKET,SO_RCVTIMEO,
                  reinterpret_cast<const char*>(&timeout),sizeof(timeout))!=0)
        return bad(3);
#else
    timeval timeout{1,500000};
    if(setsockopt(server,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))!=0)
        return bad(3);
#endif
    sockaddr_in server_addr{};
    server_addr.sin_family=AF_INET;
    server_addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    server_addr.sin_port=0;
    if(bind(server,reinterpret_cast<const sockaddr*>(&server_addr),
            sizeof(server_addr))!=0)
        return bad(4);
    test_len slen=sizeof(server_addr);
    if(getsockname(server,reinterpret_cast<sockaddr*>(&server_addr),&slen)!=0)
        return bad(5);
    auto server_key=LinkAuth::ServerKeyOf(fake_key(12));
    if(shyt_yt_server_new_v408(
        server_addr.sin_addr.s_addr,server_addr.sin_port,
        server_key.pub.data(),"fictional-id","fictional-build",""))
        return bad(6);
    auto* client=shyt_yt_server_new_v408(
        server_addr.sin_addr.s_addr,server_addr.sin_port,
        server_key.pub.data(),"fictional-id","fictional-build","fictional-secret");
    if(!client || shyt_yt_server_phase_v408(client)!=SHYT_V408_NEW)
        return bad(7);
    uint16_t client_port=0;
    if(!shyt_yt_server_local_port_v408(client,&client_port) ||
       !client_port || client_port==htons(3658))
        return bad(8);
    // Constructor alone MUST NOT transmit a datagram or create a login.
    if(shyt_yt_server_tick_v408(client,1000)!=1 ||
       shyt_yt_server_phase_v408(client)!=SHYT_V408_WAIT_COOKIE)
        return bad(9);
    sockaddr_in endpoint{};
    auto first=receive(server,endpoint);
    if(first.size()!=LinkAuth::FirstHelloBytes ||
       !std::all_of(first.begin()+LinkAuth::HelloClearBytes,first.end(),
                    [](u8 b){return b==0;}))
        return bad(10);
    LinkAuth::Cookie cookie{};
    for(size_t i=0;i<cookie.size();++i)
        cookie[i]=static_cast<u8>(i+19);
    if(!send_to(server,endpoint,YT::EncodeCookie(cookie,0,server_key.pub)))
        return bad(11);
    if(shyt_yt_server_tick_v408(client,1100)!=1 ||
       shyt_yt_server_phase_v408(client)!=SHYT_V408_WAIT_WELCOME)
        return bad(12);
    const auto second=receive(server,endpoint);
    std::vector<u8> plaintext;
    auto responder=LinkAuth::Responder::Open(server_key,second,plaintext);
    if(!responder)return bad(13);
    YT::Hello desired{};
    desired.online_id="fictional-id";
    desired.build="fictional-build";
    desired.secret="fictional-secret";
    desired.cookie=cookie;
    if(plaintext!=YT::Encode(desired))return bad(14);
    // An attacker can spoof the actual UDP server IP/port, but cannot
    // make a valid Noise NK second-handshake MAC. Never allow a fake
    // Work challenge or Redirect to force terminal login failure.
    if(!send_to(server,endpoint,YT::EncodeWork(5)) ||
       shyt_yt_server_tick_v408(client,1150)!=1 ||
       shyt_yt_server_phase_v408(client)!=SHYT_V408_WAIT_WELCOME)
        return bad(27);
    const std::vector<u8> spoof_redirect{
        0xff,0xff,0xff,0xff,'S','H','L','K',11u,0u};
    if(!send_to(server,endpoint,spoof_redirect) ||
       shyt_yt_server_tick_v408(client,1155)!=1 ||
       shyt_yt_server_phase_v408(client)!=SHYT_V408_WAIT_WELCOME)
        return bad(28);
    ShytYtServerCountersV408 before_welcome{};
    if(!shyt_yt_server_counters_v408(client,&before_welcome) ||
       before_welcome.auth_errors<2)
        return bad(29);
    // A real hosted server requires original SHA256(cookie,id,nonce)
    // for a new account. The authentic Noise NK Work challenge MUST be
    // solved on a cancellable worker without blocking any game frame.
    auto valid_work=responder->Answer(YT::EncodeWork(10),fake_key(49));
    if(!send_to(server,endpoint,valid_work.datagram) ||
       shyt_yt_server_tick_v408(client,1160)!=1)
        return bad(30);
    ShytYtServerCountersV408 work_counters{};
    bool sent_work_hello=false;
    for(unsigned attempt=0;attempt<200u;++attempt) {
        if(shyt_yt_server_tick_v408(client,1161+attempt)!=1)
            return bad(31);
        if(!shyt_yt_server_counters_v408(client,&work_counters))
            return bad(32);
        if(shyt_yt_server_phase_v408(client)==SHYT_V408_WAIT_WELCOME &&
           work_counters.hello_sent==3u) {
            sent_work_hello=true;
            break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    if(!sent_work_hello ||
       work_counters.verified_work_challenges!=1u ||
       work_counters.work_nonces_solved!=1u)
        return bad(33);
    const auto third=receive(server,endpoint);
    std::vector<u8> completed_hello;
    auto approved_work_responder=LinkAuth::Responder::Open(
        server_key,third,completed_hello);
    const auto decoded_hello=YT::DecodeHello(completed_hello);
    if(!approved_work_responder || !decoded_hello ||
       !decoded_hello->work ||
       decoded_hello->online_id!="fictional-id" ||
       decoded_hello->secret!="fictional-secret" ||
       !LinkAuth::WorkDone(cookie,"fictional-id",*decoded_hello->work,10))
        return bad(34);
    const auto welcome=YT::Encode(YT::Welcome{true,"fictional-joined"});
    auto answer=approved_work_responder->Answer(welcome,fake_key(55));
    if(!send_to(server,endpoint,answer.datagram))
        return bad(15);
    if(shyt_yt_server_tick_v408(client,1200)!=1 ||
       shyt_yt_server_phase_v408(client)!=SHYT_V408_LINKED)
        return bad(16);
    ShytYtServerCountersV408 counts{};
    if(!shyt_yt_server_counters_v408(client,&counts) ||
       counts.hello_sent!=3 || counts.heartbeats_sent!=1)
        return bad(17);
    // The authenticated heartbeat must use the ORIGINAL YT session keys.
    auto ping_wire=receive(server,endpoint);
    if(ping_wire.empty() ||
       answer.session.Open(ping_wire)!=LinkAuth::Session::Verdict::Ok)
        return bad(18);
    ping_wire.resize(ping_wire.size()-LinkAuth::TrailerBytes);
    const auto yt_ping=YT::DecodePing(YT::Kind::Ping,ping_wire);
    if(!yt_ping || yt_ping->sent_ms!=1200)
        return bad(19);
    auto yt_pong=YT::Encode(YT::Kind::Pong,*yt_ping);
    auto pong_tag=answer.session.Seal(yt_pong);
    yt_pong.insert(yt_pong.end(),pong_tag.begin(),pong_tag.end());
    if(!send_to(server,endpoint,yt_pong) ||
       shyt_yt_server_tick_v408(client,1300)!=1)
        return bad(20);
    if(!shyt_yt_server_counters_v408(client,&counts) ||
       counts.heartbeats_received!=1)
        return bad(21);

    // Real encrypted Data and Coop messages must be authenticated, but
    // WITHOUT room membership the engine must quarantine ALL payloads.
    const std::array<u8,9> fake_game{{
        0xff,0xff,0xff,0xff,0x91,0x92,0x93,0x94,0x95}};
    const auto send_encrypted=[&](std::vector<u8> raw) {
        auto trailer=answer.session.Seal(raw);
        raw.insert(raw.end(),trailer.begin(),trailer.end());
        return send_to(server,endpoint,raw);
    };
    // V412: real YT Link::Member is an encrypted PRESENCE notice, not
    // a co-op team authorization or permission to forward game data.
    ShytYtMemberNoticeV412 member_event{};
    if(shyt_yt_server_take_member_v412(client,&member_event)!=0)
        return bad(35);
    YT::Member quiet{};
    quiet.state=YT::MemberState::Quiet;
    quiet.gap_ms=1750u;
    quiet.addr_nbo=htonl(0x0a020304u);
    quiet.port_nbo=htons(3658);
    quiet.online_id="fictional-peer";
    if(!send_encrypted(YT::Encode(quiet)) ||
       shyt_yt_server_tick_v408(client,1350)!=1 ||
       shyt_yt_server_take_member_v412(client,&member_event)!=1 ||
       member_event.state!=0 ||
       member_event.gap_ms!=1750u ||
       member_event.addr_nbo!=quiet.addr_nbo ||
       member_event.port_nbo!=quiet.port_nbo ||
       std::strcmp(member_event.online_id,"fictional-peer")!=0 ||
       shyt_yt_server_take_member_v412(client,&member_event)!=0)
        return bad(36);
    // A valid Noise tag does not make a malformed Member state valid.
    auto bad_member=YT::Encode(quiet);
    bad_member[YT::HeaderSize]=0xffu;
    if(!send_encrypted(bad_member) ||
       shyt_yt_server_tick_v408(client,1360)!=1 ||
       !shyt_yt_server_counters_v408(client,&counts) ||
       counts.rejected_member_notices!=1u ||
       shyt_yt_server_take_member_v412(client,&member_event)!=0)
        return bad(37);

    if(!send_encrypted(YT::EncodeData(0x12345678u,0x4a5bu,fake_game)) ||
       !send_encrypted(YT::EncodeCoop(fake_game)) ||
       shyt_yt_server_tick_v408(client,1400)!=1)
        return bad(22);
    if(!shyt_yt_server_counters_v408(client,&counts) ||
       counts.authenticated_data_quarantined!=1 ||
       counts.authenticated_coop_quarantined!=1 ||
       counts.coop_frames_reassembled_v413!=0u ||
       counts.coop_frames_rejected_v413!=1u)
        return bad(23);
    // A REAL YT reliable CoopStream frame over the authenticated OS UDP
    // server socket is now reassembled, but never injected into BBHost.
    BloodborneCoop::CoopStream server_world("shadnet", 777u);
    const std::vector<u8> imaginary_world_state(2600u,0x5au);
    server_world.Send(imaginary_world_state,1401);
    const auto original_frames=server_world.Flush(1401);
    if(original_frames.size()<3u)return bad(41);
    for(const auto& body:original_frames) {
        if(!send_encrypted(YT::EncodeCoop(body)))return bad(42);
    }
    if(shyt_yt_server_tick_v408(client,1420)!=1 ||
       !shyt_yt_server_counters_v408(client,&counts) ||
       counts.coop_frames_reassembled_v413!=original_frames.size() ||
       counts.coop_messages_held_v413!=1u ||
       counts.coop_frames_rejected_v413!=1u)
        return bad(43);
    // Even from the configured server socket, unsigned/raw game traffic
    // cannot go to the game. It must have the original Noise NK tag.
    if(!send_to(server,endpoint,YT::EncodeData(
           0x12345678u,0x4a5bu,fake_game)) ||
       shyt_yt_server_tick_v408(client,1450)!=1)
        return bad(24);
    if(!shyt_yt_server_counters_v408(client,&counts) ||
       counts.auth_errors==0 ||
       counts.authenticated_data_quarantined!=1)
        return bad(25);
    // V412: bounded notifications must fail closed rather than silently
    // missing a Gone event, which would leave stale presence behind.
    for(unsigned i=0;i<SHYT_V412_MEMBER_QUEUE_CAP+1u;++i) {
        YT::Member next=quiet;
        next.gap_ms=i;
        next.state=YT::MemberState::Gone;
        if(!send_encrypted(YT::Encode(next)))return bad(38);
    }
    if(shyt_yt_server_tick_v408(client,1500)!=1 ||
       !shyt_yt_server_counters_v408(client,&counts) ||
       counts.authenticated_member_notices!=
           SHYT_V412_MEMBER_QUEUE_CAP+2u ||
       counts.member_notice_overflows!=1u ||
       shyt_yt_server_take_member_v412(client,&member_event)!=-1 ||
       member_event.online_id[0]!=0)
        return bad(39);
    // No event can be returned from the stale queue until a fresh
    // session and authoritative room snapshot are established.
    if(shyt_yt_server_take_member_v412(client,&member_event)!=-1)
        return bad(40);
    // Original client must keep its authenticated transport, but report
    // quiet when replies have not arrived within the safety window.
    if(shyt_yt_server_tick_v408(client,12500)!=1 ||
       shyt_yt_server_phase_v408(client)!=SHYT_V408_QUIET)
        return bad(26);
    shyt_yt_server_free_v408(client);
    close_raw(server);
#ifdef _WIN32
    WSACleanup();
#endif
    std::puts("SHYT_V408_REAL_ORIGINAL_YT_SERVER_LINK_SESSION_LOGIN_HEARTBEAT_QUARANTINE_PASS");
    std::puts("SHYT_V409_SOURCE_PINNED_YT_HOSTED_SIGNUP_POW_BACKGROUND_NONCE_AND_RELOGIN_PASS");
    std::puts("SHYT_V412_MAC_AUTHENTICATED_MEMBER_PRESENCE_QUEUE_OVERFLOW_FAIL_CLOSED_PASS");
    std::puts("localhost only; encrypted game Data quarantined. No production or retail game connection.");
    return 0;
}
