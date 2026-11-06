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

    // V416: a connected BBHost plugin does NOT silently log into the
    // lobby: explicit caller opt-in is required. No guest/NetSync access.
    const char invalid_utf8[]={char(0xc0),char(0xaf),0};
    if(shyt_yt_server_send_lobby_hello_v416(client,invalid_utf8,0,1301)!=0 ||
       shyt_yt_server_send_lobby_hello_v416(client,"Hunter Test",2,1301)!=0 ||
       shyt_yt_server_send_lobby_hello_v416(client,"",0,1301)!=0)
        return bad(53);
    if(shyt_yt_server_send_lobby_hello_v416(client,"Hunter Test",0,1301)!=1 ||
       shyt_yt_server_send_lobby_hello_v416(client,"Hunter Test",0,1302)!=0)
        return bad(54);
    auto login_coop_wire=receive(server,endpoint);
    if(login_coop_wire.empty() ||
       answer.session.Open(login_coop_wire)!=LinkAuth::Session::Verdict::Ok)
        return bad(55);
    login_coop_wire.resize(login_coop_wire.size()-LinkAuth::TrailerBytes);
    const auto login_frame=YT::DecodeCoop(login_coop_wire);
    if(!login_frame)return bad(56);
    // This receiver represents THE SAME server run as server_world.
    // A real client now echoes the authenticated server's instance in
    // GameFrame.peer_instance; a mismatched fake receiver drops it.
    BloodborneCoop::CoopStream from_client("shadnet",777u);
    const auto login_envelopes=from_client.Receive(*login_frame,1301);
    if(login_envelopes.size()!=1u)return bad(57);
    // Canonical protobuf (original YT Envelope.lobby_hello=23):
    // {protocol=8, member=lowercase hex authenticated ID, name, playing=0}.
    std::string member_hex;
    constexpr char hex[]="0123456789abcdef";
    for(const unsigned char c:std::string("fictional-id")) {
        member_hex.push_back(hex[c>>4u]);
        member_hex.push_back(hex[c&15u]);
    }
    std::vector<u8> expected_inner{0x08u,0x08u,0x12u,static_cast<u8>(member_hex.size())};
    expected_inner.insert(expected_inner.end(),member_hex.begin(),member_hex.end());
    const std::string display="Hunter Test";
    expected_inner.push_back(0x1au);
    expected_inner.push_back(static_cast<u8>(display.size()));
    expected_inner.insert(expected_inner.end(),display.begin(),display.end());
    std::vector<u8> expected_lobby{0xbau,0x01u,static_cast<u8>(expected_inner.size())};
    expected_lobby.insert(expected_lobby.end(),expected_inner.begin(),expected_inner.end());
    if(login_envelopes.front()!=expected_lobby)return bad(58);

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
    ShytYtCoopCountersV413 coop_counts{};
    if(!shyt_yt_server_counters_v408(client,&counts) ||
       !shyt_yt_server_coop_counters_v413(client,&coop_counts) ||
       counts.authenticated_data_quarantined!=1 ||
       counts.authenticated_coop_quarantined!=1 ||
       coop_counts.frames_reassembled!=0u ||
       coop_counts.frames_rejected!=1u)
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
       !shyt_yt_server_coop_counters_v413(client,&coop_counts) ||
       coop_counts.frames_reassembled!=original_frames.size() ||
       coop_counts.messages_held!=1u ||
       coop_counts.frames_rejected!=1u)
        return bad(43);
    // V415: real authenticated original YT CoopStream now carries the
    // canonical protobuf field tags for LobbyState/TeamStart/Welcome.
    // We construct the tiny fixture using the pinned original field tags,
    // while the separate V415 CI cross-checks actual generated protobuf.
    auto putvar=[](std::vector<u8>& dst,std::uint64_t v) {
        while(v>127u) {
            dst.push_back(static_cast<u8>((v&127u)|128u));
            v >>= 7u;
        }
        dst.push_back(static_cast<u8>(v));
    };
    auto putnum=[&](std::vector<u8>& dst,unsigned field,std::uint64_t value) {
        putvar(dst,field*8u);
        putvar(dst,value);
    };
    auto putbytes=[&](std::vector<u8>& dst,unsigned field,
                      const std::vector<u8>& bytes) {
        putvar(dst,field*8u+2u);
        putvar(dst,bytes.size());
        dst.insert(dst.end(),bytes.begin(),bytes.end());
    };
    auto puttext=[&](std::vector<u8>& dst,unsigned field,
                     const std::string& value) {
        const std::vector<u8> bytes(value.begin(),value.end());
        putbytes(dst,field,bytes);
    };
    std::vector<u8> team;
    puttext(team,1,"team-v415");
    puttext(team,2,member_hex); // original shadNet AuthenticatedMember()
    putnum(team,4,1);
    puttext(team,6,"world-v415");
    puttext(team,7,"world:world-v415");
    for(unsigned i=0;i<5u;++i) {
        std::vector<u8> m;
        // Every lobby TeamMember.member is an authenticated online ID
        // converted to lower-case hex, never the display name.
        const std::string raw=i==0u?"fictional-id":"hunter"+std::to_string(i+1u);
        std::string id;
        for(unsigned char c:raw) {
            id.push_back(hex[c>>4u]);
            id.push_back(hex[c&15u]);
        }
        puttext(m,1,id);
        putnum(m,4,1);
        putnum(m,5,i+1u);
        if(i>0u)putnum(m,7,8u-i); // guest signs 7,6,5,4
        putbytes(team,3,m);
    }
    // Original v1.4 initial LobbyState often has no team at all.
    // It is a valid protobuf oneof with an empty nested message.
    const std::vector<u8> teamless_lobby{0xcau,0x01u,0x00u};
    server_world.Send(teamless_lobby,1421);
    for(const auto& frame:server_world.Flush(1421))
        if(!send_encrypted(YT::EncodeCoop(frame)))return bad(59);
    if(shyt_yt_server_tick_v408(client,1421)!=1)return bad(60);
    std::vector<u8> lobby, lobby_envelope;
    putbytes(lobby,1,team);
    putbytes(lobby_envelope,25,lobby);
    server_world.Send(lobby_envelope,1421);
    for(const auto& frame:server_world.Flush(1421))
        if(!send_encrypted(YT::EncodeCoop(frame)))return bad(44);
    if(shyt_yt_server_tick_v408(client,1422)!=1)return bad(45);
    std::vector<u8> start, start_envelope;
    puttext(start,1,"team-v415");
    puttext(start,2,"world:world-v415");
    puttext(start,3,member_hex);
    putnum(start,4,1);
    puttext(start,5,"world-v415");
    putbytes(start_envelope,26,start);
    server_world.Send(start_envelope,1423);
    for(const auto& frame:server_world.Flush(1423))
        if(!send_encrypted(YT::EncodeCoop(frame)))return bad(46);
    if(shyt_yt_server_tick_v408(client,1424)!=1)return bad(47);
    // V418: only a game-confirmed save slot and authentic TeamStart may
    // cause a party Hello. These negative cases MUST send no datagrams.
    if(shyt_yt_server_send_party_hello_v418(
           client,"world:another",1u,707u,1,1424)!=0 ||
       shyt_yt_server_send_party_hello_v418(
           client,"world:world-v415",2u,707u,1,1424)!=0 ||
       shyt_yt_server_send_party_hello_v418(
           client,"world:world-v415",1u,0u,1,1424)!=0 ||
       shyt_yt_server_send_party_hello_v418(
           client,"world:world-v415",1u,707u,2,1424)!=0)
        return bad(61);
    if(shyt_yt_server_send_party_hello_v418(
           client,"world:world-v415",1u,707u,1,1424)!=1 ||
       shyt_yt_server_send_party_hello_v418(
           client,"world:world-v415",1u,707u,1,1424)!=0)
        return bad(62);
    // Original YT Envelope.hello = 1, Hello fields:
    // protocol=1, party=2, authenticated member=3, run=4,
    // host=5 (server leader), enemy_owner=6.
    std::vector<u8> expected_party_hello,expected_party_envelope;
    putnum(expected_party_hello,1,8u);
    puttext(expected_party_hello,2,"world:world-v415");
    puttext(expected_party_hello,3,member_hex);
    putnum(expected_party_hello,4,707u);
    putnum(expected_party_hello,5,1u); // our fictional member is host
    putnum(expected_party_hello,6,1u);
    putbytes(expected_party_envelope,1,expected_party_hello);
    bool party_hello_seen=false;
    for(unsigned attempts=0;attempts<16u && !party_hello_seen;++attempts) {
        auto reply=receive(server,endpoint);
        if(reply.empty())return bad(63);
        if(answer.session.Open(reply)!=LinkAuth::Session::Verdict::Ok)
            return bad(64);
        reply.resize(reply.size()-LinkAuth::TrailerBytes);
        if(const auto coop=YT::DecodeCoop(reply)) {
            for(const auto& original_message:
                from_client.Receive(*coop,1424)) {
                if(original_message==expected_party_envelope)
                    party_hello_seen=true;
            }
        }
    }
    if(!party_hello_seen)return bad(65);
    // Nothing above grants a BBHost P2P/NetSync/game-memory permission.
    // World Welcome remains unbound until the next explicit world gate.
    std::vector<u8> party_welcome, welcome_envelope;
    putnum(party_welcome,1,1); // accepted, but no separate party link binding
    putnum(party_welcome,3,77); // synthetic world epoch
    putbytes(welcome_envelope,2,party_welcome);
    server_world.Send(welcome_envelope,1425);
    for(const auto& frame:server_world.Flush(1425))
        if(!send_encrypted(YT::EncodeCoop(frame)))return bad(48);
    if(shyt_yt_server_tick_v408(client,1426)!=1)return bad(49);
    ShytYtTeamObservationsV415 observations{};
    ShytYtPartyReplyObservationsV419 party_replies{};
    if(!shyt_yt_server_team_observations_v415(client,&observations) ||
       !shyt_yt_server_party_observations_v419(client,&party_replies) ||
       !shyt_yt_server_coop_counters_v413(client,&coop_counts) ||
       observations.lobby_states_accepted!=2u ||
       observations.team_starts_accepted!=1u ||
       observations.party_welcomes_unbound!=0u ||
       party_replies.party_hellos_sent!=1u ||
       party_replies.replies_correlated!=1u ||
       party_replies.replies_unbound!=0u ||
       party_replies.candidate_awaiting_snapshot!=1u ||
       observations.authority_messages_rejected!=1u ||
       coop_counts.messages_held!=1u)
        return bad(50);
    // Only arbitrary unhandled world data remains quarantined. V419
    // correlated the Welcome with explicit party Hello, but it is still
    // a read-only candidate, NOT permission for NetSync or game writes.
    // V420: explicitly ask for the first full world snapshot over the
    // SAME Noise NK-authenticated original reliable YT CoopStream.
    // The canonical initial request {epoch:0,seq:0} contains no local
    // game state and grants no NetSync access.
    if(shyt_yt_server_send_snapshot_request_v420(client,1427)!=1 ||
       shyt_yt_server_send_snapshot_request_v420(client,1427)!=0)
        return bad(66);
    const std::vector<u8> expected_snapshot_request{0x32u,0x00u};
    bool saw_snapshot_request=false;
    for(unsigned attempt=0;attempt<16u && !saw_snapshot_request;++attempt) {
        auto reply=receive(server,endpoint);
        if(reply.empty())return bad(67);
        if(answer.session.Open(reply)!=LinkAuth::Session::Verdict::Ok)
            return bad(68);
        reply.resize(reply.size()-LinkAuth::TrailerBytes);
        if(const auto coop=YT::DecodeCoop(reply)) {
            for(const auto& message:from_client.Receive(*coop,1427))
                if(message==expected_snapshot_request)
                    saw_snapshot_request=true;
        }
    }
    if(!saw_snapshot_request)return bad(69);
    // A real original field-tag Snapshot (Envelope.snapshot=7) arrives.
    // Its payload is deliberately retained in quarantine: observing the
    // epoch/last header is NOT applying map kills/flags/HP to the game.
    std::vector<u8> snapshot_body,snapshot_envelope;
    putnum(snapshot_body,1u,77u); // epoch from accepted party Welcome
    putnum(snapshot_body,2u,9u); // original world last sequence
    std::vector<u8> one_map;
    putnum(one_map,1u,0x18000000u);
    std::vector<u8> packed_handles;
    putvar(packed_handles,55u);
    putvar(packed_handles,300u);
    putbytes(one_map,2u,packed_handles);
    putbytes(snapshot_body,3u,one_map); // MapKills (packed uint32)
    std::vector<u8> shown_character;
    putnum(shown_character,1u,55u);
    putnum(shown_character,2u,7u);
    putbytes(snapshot_body,5u,shown_character);
    putnum(snapshot_body,6u,0x18000000u); // map_state_map
    putbytes(snapshot_body,7u,std::vector<u8>(64u,0x5au));
    std::vector<u8> one_hp;
    putnum(one_hp,1u,0x123456789u); // source
    putnum(one_hp,2u,0x18000000u); // map
    std::vector<u8> hp_enemy;
    putnum(hp_enemy,1u,55u);
    putnum(hp_enemy,2u,101u); // sint32 -51 zigzag=101
    putnum(hp_enemy,3u,200u); // sint32 100 zigzag=200
    putbytes(one_hp,3u,hp_enemy);
    putbytes(snapshot_body,10u,one_hp);
    std::vector<u8> one_flag;
    putnum(one_flag,1u,7u); // 7 <= snapshot last=9
    putnum(one_flag,2u,0x18000000u);
    putnum(one_flag,3u,1u);
    putnum(one_flag,4u,1200u);
    putnum(one_flag,5u,1u);
    putbytes(snapshot_body,11u,one_flag);
    putnum(snapshot_body,12u,1u); // after_wipe
    putbytes(snapshot_envelope,7u,snapshot_body);
    server_world.Send(snapshot_envelope,1428);
    for(const auto& frame:server_world.Flush(1428))
        if(!send_encrypted(YT::EncodeCoop(frame)))return bad(70);
    if(shyt_yt_server_tick_v408(client,1429)!=1)return bad(71);
    ShytYtWorldSnapshotObservationsV420 world_observations{};
    if(!shyt_yt_server_world_observations_v420(client,&world_observations) ||
       !shyt_yt_server_coop_counters_v413(client,&coop_counts) ||
       world_observations.requests_sent!=1u ||
       world_observations.metadata_matching!=1u ||
       world_observations.metadata_rejected!=0u ||
       world_observations.awaiting_game_snapshot_consumer!=1u ||
       coop_counts.messages_held!=2u)
        return bad(72);
    // An inner frame from a different identity cannot impersonate shadnet
    // even when the outer authenticated test server sends it.
    BloodborneCoop::CoopStream impostor("not-shadnet",800u);
    impostor.Send(lobby_envelope,1430);
    for(const auto& frame:impostor.Flush(1430))
        if(!send_encrypted(YT::EncodeCoop(frame)))return bad(51);
    if(shyt_yt_server_tick_v408(client,1431)!=1 ||
       !shyt_yt_server_coop_counters_v413(client,&coop_counts) ||
       coop_counts.frames_rejected!=2u ||
       !shyt_yt_server_team_observations_v415(client,&observations) ||
       observations.lobby_states_accepted!=2u)
        return bad(52);
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
       !shyt_yt_server_coop_counters_v413(client,&coop_counts) ||
       coop_counts.fail_closed!=1u ||
       coop_counts.messages_held!=0u ||
       !shyt_yt_server_party_observations_v419(client,&party_replies) ||
       party_replies.candidate_awaiting_snapshot!=0u ||
       party_replies.contexts_revoked!=1u ||
       !shyt_yt_server_world_observations_v420(client,&world_observations) ||
       world_observations.awaiting_game_snapshot_consumer!=0u ||
       world_observations.contexts_revoked!=1u ||
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
       shyt_yt_server_phase_v408(client)!=SHYT_V408_QUIET ||
       !shyt_yt_server_coop_counters_v413(client,&coop_counts) ||
       coop_counts.fail_closed!=1u ||
       coop_counts.messages_held!=0u)
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
