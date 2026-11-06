// SPDX-License-Identifier: GPL-2.0-or-later
// V408: explicit-opt-in original YT SHLK4 session controller over native UDP.
// NO network at BBHost plugin load. NO Fornex address, account or retail data.
// Authentication via original YT Noise NK; received guest Data/Coop kept
// QUARANTINED until original room and map/owner permission verification.
#include "shyt_yt_server_session_v408.h"
#include "shyt_yt_udp_endpoint_v406.h"
#include "shyt_yt_shlk_client_v401.h"
#include "shyt_yt_link_wire_v403.h"
#include "shyt_yt_signup_work_v409.h"
#include "shyt_yt_coop_transport_v413.h"
#include "shyt_yt_team_authority_v414.h"
#include "shyt_yt_team_wire_lite_v415.h"
#include "core/libraries/network/net_link.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <new>
#include <memory>
#include <string>
#include <vector>
#if defined(_WIN32)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <bcrypt.h>
#elif defined(__linux__)
#include <cerrno>
#include <sys/random.h>
#else
#include <cstdlib>
#endif

namespace YT=Libraries::Net::Link;
static_assert(YT::LinkVersion==4);
static constexpr uint64_t kHelloRetry=1000u;
static constexpr uint64_t kHeartbeat=1000u;
static constexpr uint64_t kQuiet=10000u;
static constexpr unsigned kPollBudget=32u;
static constexpr size_t kWireLimit=SHYT_YT_UDP_MAX_DATAGRAM_V406;

struct ShytYtServerSessionV408 {
    ShytYtUdpEndpointV406* udp=nullptr;
    ShytYtShlkClientV401* auth=nullptr;
    std::string online_id,build,secret;
    LinkAuth::Cookie cookie{};
    int phase=SHYT_V408_NEW;
    bool has_cookie=false;
    uint64_t last_hello=0, last_ping=0, last_auth_recv=0, last_tick=0;
    uint32_t pending_ping_seq=0, next_seq=0;
    bool ping_outstanding=false;
    ShytYtServerCountersV408 counters{};
    ShytYtCoopCountersV413 coop_counters{};
    ShytYtTeamObservationsV415 team_observations{};
    std::unique_ptr<SeamlessHunt::YtTeamAuthorityV414> team_gate;
    size_t coop_observed=0;
    // V412: only authenticated transport presence, never team approval.
    std::array<ShytYtMemberNoticeV412,SHYT_V412_MEMBER_QUEUE_CAP> member_queue{};
    size_t member_head=0,member_count=0;
    bool member_overflow=false;
    // Original YT ordered Coop stream, authenticated frames held in quarantine.
    // This is NOT room membership and cannot feed BBHost game NetSync.
    std::unique_ptr<SeamlessHunt::CoopTransportV413> coop_quarantine;
    ShytYtSignupWorkV409* signup_work=nullptr;
    int signup_work_bits=0;
};

namespace {
void wipe_v408(void* ptr,size_t n) noexcept {
    volatile uint8_t* p=static_cast<volatile uint8_t*>(ptr);
    if(!p)return;
    for(size_t i=0;i<n;++i)p[i]=0;
}
bool entropy_v408(uint8_t* output,size_t n) noexcept {
    if(!output || n==0 || n>32u)return false;
#if defined(_WIN32)
    return BCryptGenRandom(nullptr,output,static_cast<ULONG>(n),
                           BCRYPT_USE_SYSTEM_PREFERRED_RNG)>=0;
#elif defined(__linux__)
    size_t count=0;
    while(count<n) {
        const ssize_t got=getrandom(output+count,n-count,0);
        if(got<0) {
            if(errno==EINTR)continue;
            return false;
        }
        if(!got)return false;
        count+=static_cast<size_t>(got);
    }
    return true;
#else
    arc4random_buf(output,n);
    return true;
#endif
}
bool valid_field(const char* s) noexcept {
    if(!s)return false;
    // Real YT PutText caps fields at 255: reject rather than silently
    // truncating an online ID, version or account secret.
    for(size_t i=0;i<=255u;++i) {
        if(s[i]==0)return i>=1u;
    }
    return false;
}
bool maybe_later(uint64_t now,uint64_t previous,uint64_t delay) noexcept {
    return now>=previous && now-previous>=delay;
}
void reject(ShytYtServerSessionV408& s) noexcept {
    ++s.counters.rejected_control_packets;
}
void invalidate_coop(ShytYtServerSessionV408& s) noexcept {
    if(s.team_gate)s.team_gate->Revoke();
    s.coop_observed=0;
    if(s.coop_quarantine && s.coop_quarantine->Invalidate()) {
        ++s.coop_counters.fail_closed;
        s.coop_counters.messages_held=0;
    }
}
// V415: READ-ONLY observation on the authenticated link, never an auth
// grant. In particular an unbound party Welcome cannot call
// OnAuthenticatedPartyWelcome(). Reliable world data stays quarantined
// and no game/NetSync callback is invoked.
void observe_team_authority(ShytYtServerSessionV408& s) {
    if(!s.team_gate || !s.coop_quarantine)return;
    std::span<const u8> bytes;
    while(s.coop_quarantine->PeekQuarantined(s.coop_observed,bytes)) {
        ++s.coop_observed;
        auto decoded=SeamlessHunt::YtTeamWireLiteV415::Decode(bytes);
        using Kind=SeamlessHunt::YtTeamWireLiteV415::Kind;
        switch(decoded.kind) {
        case Kind::Lobby:
            if(s.team_gate->OnAuthenticatedLobby(std::move(decoded.lobby)))
                ++s.team_observations.lobby_states_accepted;
            else
                ++s.team_observations.authority_messages_rejected;
            break;
        case Kind::Start:
            if(s.team_gate->OnAuthenticatedTeamStart(decoded.start))
                ++s.team_observations.team_starts_accepted;
            else
                ++s.team_observations.authority_messages_rejected;
            break;
        case Kind::Welcome:
            // The stream's party identity has NOT been established.
            ++s.team_observations.party_welcomes_unbound;
            break;
        case Kind::Invalid:
            s.team_gate->Revoke();
            ++s.team_observations.authority_messages_rejected;
            break;
        case Kind::Other:
            break;
        }
    }
}
bool start_hello(ShytYtServerSessionV408& s,uint64_t now) {
    std::array<uint8_t,32> ephemeral{};
    if(!entropy_v408(ephemeral.data(),ephemeral.size())) {
        s.phase=SHYT_V408_IO_FAILED;
        return false;
    }
    std::array<uint8_t,kWireLimit> wire{};
    size_t n=0;
    bool valid=false;
    if(!s.has_cookie) {
        std::array<uint8_t,LinkAuth::HelloClearBytes> first{};
        first[0]=first[1]=first[2]=first[3]=0xff;
        first[4]='S';first[5]='H';first[6]='L';first[7]='K';
        first[LinkAuth::KindAt]=LinkAuth::KindHello;
        first[LinkAuth::HeaderBytes]=YT::LinkVersion;
        valid=shyt_yt_shlk_hello_v401(
            s.auth,first.data(),first.size(),ephemeral.data(),
            wire.data(),wire.size(),&n)!=0;
        if(valid)s.phase=SHYT_V408_WAIT_COOKIE;
    } else {
        YT::Hello hello{};
        hello.online_id=s.online_id;
        hello.build=s.build;
        hello.secret=s.secret;
        hello.cookie=s.cookie;
        uint64_t solved_work=0;
        if(shyt_yt_shlk_work_nonce_v409(s.auth,&solved_work))
            hello.work=solved_work;
        std::vector<u8> plain=YT::Encode(hello);
        valid=plain.size()<=kWireLimit-64u &&
              shyt_yt_shlk_hello_v401(s.auth,plain.data(),plain.size(),
                   ephemeral.data(),wire.data(),wire.size(),&n)!=0;
        wipe_v408(hello.secret.data(),hello.secret.size());
        wipe_v408(plain.data(),plain.size());
        if(valid)s.phase=SHYT_V408_WAIT_WELCOME;
    }
    wipe_v408(ephemeral.data(),ephemeral.size());
    if(!valid || n>kWireLimit ||
       !shyt_yt_udp_send_server_v406(s.udp,wire.data(),n)) {
        s.phase=SHYT_V408_IO_FAILED;
        return false;
    }
    s.last_hello=now;
    ++s.counters.hello_sent;
    return true;
}
bool encrypt_send(ShytYtServerSessionV408& s,
                  const uint8_t* message,size_t n) {
    if(!shyt_yt_shlk_linked_v401(s.auth) || n>kWireLimit-24u)
        return false;
    std::array<uint8_t,kWireLimit> encrypted{};
    size_t size=0;
    if(!shyt_yt_shlk_seal_v401(s.auth,message,n,
          encrypted.data(),encrypted.size(),&size))
        return false;
    return shyt_yt_udp_send_server_v406(s.udp,encrypted.data(),size)!=0;
}
bool ping(ShytYtServerSessionV408& s,uint64_t now) {
    if(!s.next_seq)s.next_seq=1;
    uint8_t wire[32]={0};
    size_t n=0;
    const uint32_t seq=s.next_seq++;
    if(!shyt_yt_link_encode_ping_v403(4u,seq,now,wire,sizeof(wire),&n) ||
       !encrypt_send(s,wire,n))
        return false;
    s.pending_ping_seq=seq;
    s.ping_outstanding=true;
    s.last_ping=now;
    ++s.counters.heartbeats_sent;
    return true;
}
void handle_control(ShytYtServerSessionV408& s,
                    const uint8_t* raw,size_t n,uint64_t now) {
    const int kind=shyt_yt_link_kind_v403(raw,n);
    if(kind==9 && s.phase==SHYT_V408_WAIT_COOKIE) {
        uint8_t cookie[16]={0},server_pub[32]={0},work=0;
        if(!shyt_yt_link_decode_cookie_v403(
              raw,n,cookie,server_pub,&work) ||
           !shyt_yt_shlk_cookie_v401(s.auth,cookie,server_pub)) {
            reject(s);
            return;
        }
        // A cookie advertises work difficulty, but the original YT
        // server sends an authenticated Work response ONLY if the
        // account is new and actually needs the one-time challenge.
        // Existing accounts must not waste CPU on a cookie hint.
        if(work>LinkAuth::MaxWorkBits) {
            s.phase=SHYT_V408_WORK_UNSUPPORTED;
            return;
        }
        std::copy(cookie,cookie+sizeof(cookie),s.cookie.begin());
        s.has_cookie=true;
        (void)start_hello(s,now);
        return;
    }
    if((kind==10 && s.phase==SHYT_V408_WAIT_WELCOME) ||
       (kind==11 && (s.phase==SHYT_V408_WAIT_WELCOME ||
                      s.phase==SHYT_V408_LINKED ||
                      s.phase==SHYT_V408_QUIET))) {
        // Work and Redirect are Noise NK answers, not plain commands.
        // A spoofed datagram with KindWork/KindRedirect must NEVER be
        // allowed to stop login or change server state before MAC check.
        std::array<uint8_t,kWireLimit> verified{};
        size_t verified_size=0;
        if(!shyt_yt_shlk_open_v401(s.auth,raw,n,
              verified.data(),verified.size(),&verified_size) ||
           shyt_yt_link_kind_v403(verified.data(),verified_size)!=kind) {
            ++s.counters.auth_errors;
            return;
        }
        if(kind==10) {
            const auto asked=YT::DecodeWork({verified.data(),verified_size});
            if(!asked || *asked<1 || *asked>28 ||
               !shyt_yt_shlk_work_challenge_v409(s.auth,*asked)) {
                ++s.counters.work_challenges_refused;
                s.phase=SHYT_V408_WORK_UNSUPPORTED;
                return;
            }
            // Windows minwindef.h can define min as a macro: never
            // let its preprocessor substitution enter the C++ code.
            const int exponent=(*asked+5>29)?29:(*asked+5);
            const uint64_t attempts=uint64_t{1}<<exponent;
            s.signup_work=shyt_yt_work_start_v409(
                s.cookie.data(),s.online_id.c_str(),*asked,attempts);
            if(!s.signup_work) {
                ++s.counters.work_challenges_refused;
                s.phase=SHYT_V408_WORK_UNSUPPORTED;
                return;
            }
            s.signup_work_bits=*asked;
            ++s.counters.verified_work_challenges;
            s.phase=SHYT_V408_SOLVING_WORK;
            return;
        }
        // A shard redirect needs a pinned key plus an authenticated
        // region ticket; never follow an address from unverified input.
        s.phase=SHYT_V408_REDIRECT_UNSUPPORTED;
        return;
    }
    // EVERYTHING else, including Welcome and Data, MUST decrypt before
    // parsing. V401 enforces YT's Noise NK authentication and replay.
    if(s.phase==SHYT_V408_WAIT_WELCOME ||
       s.phase==SHYT_V408_LINKED ||
       s.phase==SHYT_V408_QUIET) {
        std::array<uint8_t,kWireLimit> plain{};
        size_t size=0;
        if(!shyt_yt_shlk_open_v401(s.auth,raw,n,
               plain.data(),plain.size(),&size)) {
            ++s.counters.auth_errors;
            return;
        }
        const int decrypted_kind=shyt_yt_link_kind_v403(plain.data(),size);
        if(s.phase==SHYT_V408_WAIT_WELCOME) {
            if(decrypted_kind!=2 || !shyt_yt_shlk_linked_v401(s.auth)) {
                reject(s);
                return;
            }
            char reason[256]={0};
            int accepted=0;
            if(!shyt_yt_link_decode_welcome_v403(
                 plain.data(),size,&accepted,reason,sizeof(reason))) {
                reject(s);
                return;
            }
            s.phase=accepted?SHYT_V408_LINKED:SHYT_V408_REFUSED;
            s.last_auth_recv=now;
            return;
        }
        if(decrypted_kind==5) {
            uint32_t seq=0;uint64_t sent=0;
            if(shyt_yt_link_decode_ping_v403(
                  5u,plain.data(),size,&seq,&sent) &&
               s.ping_outstanding && seq==s.pending_ping_seq &&
               sent==s.last_ping && now>=sent) {
                ++s.counters.heartbeats_received;
                s.ping_outstanding=false;
                s.last_auth_recv=now;
                s.phase=SHYT_V408_LINKED;
            }else reject(s);
            return;
        }
        if(decrypted_kind==6) {
            // V412: original YT's LINK presence notifications (Quiet,
            // Back, Gone) are not proof of membership in a co-op room.
            // Only process after successful Noise NK MAC/replay checks.
            const auto notice=YT::DecodeMember({plain.data(),size});
            if(!notice || notice->online_id.empty() ||
               notice->online_id.size()>255u) {
                ++s.counters.rejected_member_notices;
                return;
            }
            s.last_auth_recv=now;
            s.phase=SHYT_V408_LINKED;
            ++s.counters.authenticated_member_notices;
            if(s.member_overflow)return; // fail closed until new session
            if(s.member_count==SHYT_V412_MEMBER_QUEUE_CAP) {
                s.member_overflow=true;
                s.member_head=0;
                s.member_count=0;
                ++s.counters.member_notice_overflows;
                // Lost member presence invalidates room/world authority.
                // Old reliable world events must not survive it.
                invalidate_coop(s);
                return;
            }
            ShytYtMemberNoticeV412 event{};
            event.state=static_cast<uint8_t>(notice->state);
            event.gap_ms=notice->gap_ms;
            event.addr_nbo=notice->addr_nbo;
            event.port_nbo=notice->port_nbo;
            std::memcpy(event.online_id,notice->online_id.data(),
                        notice->online_id.size());
            event.online_id[notice->online_id.size()]=0;
            s.member_queue[(s.member_head+s.member_count)%
                           SHYT_V412_MEMBER_QUEUE_CAP]=event;
            ++s.member_count;
            return;
        }
        if(decrypted_kind==3) {
            // Authenticated != authorized for the guest. The server
            // must explicitly approve this peer's room/map ownership
            // before ANY frame is injected into BBHost NetSync.
            std::array<uint8_t,kWireLimit> held{};
            uint32_t addr=0;uint16_t port=0;size_t game_size=0;
            if(shyt_yt_link_decode_data_v403(
                  plain.data(),size,&addr,&port,
                  held.data(),held.size(),&game_size)) {
                ++s.counters.authenticated_data_quarantined;
                s.last_auth_recv=now;
                s.phase=SHYT_V408_LINKED;
                wipe_v408(held.data(),game_size);
            } else reject(s);
            return;
        }
        if(decrypted_kind==7) {
            std::array<uint8_t,kWireLimit> held{};
            size_t body_size=0;
            if(shyt_yt_link_decode_coop_v403(
                  plain.data(),size,held.data(),held.size(),&body_size)) {
                ++s.counters.authenticated_coop_quarantined;
                // V413: only original YT GameFrames are accepted into the
                // bounded stream after the server's Noise NK MAC/replay gate.
                // Completed envelopes remain quarantined, NOT game-authorized.
                if(s.coop_quarantine &&
                   s.coop_quarantine->ReceiveAfterServerAuth(
                       std::span<const u8>{held.data(),body_size},
                       static_cast<s64>(now))) {
                    ++s.coop_counters.frames_reassembled;
                    observe_team_authority(s);
                    s.coop_counters.messages_held=
                        s.coop_quarantine->Quarantined();
                } else {
                    ++s.coop_counters.frames_rejected;
                    if(s.coop_quarantine && s.coop_quarantine->Failed()) {
                        // Already invalidated inside the bounded adapter;
                        // record the transition once and keep held count zero.
                        if(s.coop_counters.fail_closed==0u)
                            ++s.coop_counters.fail_closed;
                        s.coop_counters.messages_held=0;
                    }
                }
                s.last_auth_recv=now;
                s.phase=SHYT_V408_LINKED;
                wipe_v408(held.data(),body_size);
            } else reject(s);
            return;
        }
        // Server Member and Rpc messages require authenticated team/NP
        // state transition modules; never hand raw bytes to the game.
        reject(s);
    } else {
        reject(s);
    }
}
}
extern "C" ShytYtServerSessionV408 *shyt_yt_server_new_v408(
    uint32_t server_ip_nbo,uint16_t server_port_nbo,
    const uint8_t pinned_server_pub[32],
    const char* online_id,const char* game_build,const char* secret) {
    if(!pinned_server_pub || !valid_field(online_id) ||
       !valid_field(game_build) || !valid_field(secret))
        return nullptr;
    ShytYtServerSessionV408* session=nullptr;
    try {
        session=new(std::nothrow) ShytYtServerSessionV408{};
        if(!session)return nullptr;
        session->auth=shyt_yt_shlk_new_v401();
        if(!session->auth ||
           !shyt_yt_shlk_pin_v401(session->auth,pinned_server_pub)) {
            shyt_yt_server_free_v408(session);
            return nullptr;
        }
        session->udp=shyt_yt_udp_open_v406(server_ip_nbo,server_port_nbo);
        if(!session->udp) {
            shyt_yt_server_free_v408(session);
            return nullptr;
        }
        session->online_id=online_id;
        session->build=game_build;
        session->secret=secret;
        // Unique per-link reliability instance. No network is initiated and
        // no game data is authorized by constructing this stream.
        std::array<uint8_t,4> run_entropy{};
        if(!entropy_v408(run_entropy.data(),run_entropy.size())) {
            shyt_yt_server_free_v408(session);
            return nullptr;
        }
        const u32 run=u32{run_entropy[0]} |
             (u32{run_entropy[1]}<<8) |
             (u32{run_entropy[2]}<<16) |
             (u32{run_entropy[3]}<<24);
        session->coop_quarantine=
            std::make_unique<SeamlessHunt::CoopTransportV413>(
                session->online_id,run==0u?1u:run,"shadnet");
        session->team_gate=
            std::make_unique<SeamlessHunt::YtTeamAuthorityV414>(session->online_id);
        return session;
    } catch(...) {
        shyt_yt_server_free_v408(session);
        return nullptr;
    }
}
extern "C" void shyt_yt_server_free_v408(ShytYtServerSessionV408* s) {
    if(!s)return;
    shyt_yt_work_free_v409(s->signup_work);
    wipe_v408(s->secret.data(),s->secret.size());
    shyt_yt_shlk_free_v401(s->auth);
    shyt_yt_udp_close_v406(s->udp);
    delete s;
}
extern "C" int shyt_yt_server_tick_v408(
    ShytYtServerSessionV408* s,uint64_t now) {
    if(!s || !s->udp || !s->auth)return -1;
    if(s->phase>=SHYT_V408_REFUSED)return 1;
    if(now<s->last_tick)return 1;
    s->last_tick=now;
    try {
        if(s->phase==SHYT_V408_NEW ||
           ((s->phase==SHYT_V408_WAIT_COOKIE ||
             s->phase==SHYT_V408_WAIT_WELCOME) &&
            maybe_later(now,s->last_hello,kHelloRetry))) {
            if(!start_hello(*s,now))return -1;
        }
        for(unsigned i=0;i<kPollBudget;++i) {
            std::array<uint8_t,kWireLimit> wire{};
            size_t n=0;
            const int read=shyt_yt_udp_receive_server_v406(
                s->udp,wire.data(),wire.size(),&n);
            if(read<0) {
                invalidate_coop(*s);
                s->phase=SHYT_V408_IO_FAILED;
                return -1;
            }
            if(!read)break;
            handle_control(*s,wire.data(),n,now);
            if(s->phase>=SHYT_V408_REFUSED)break;
        }
        if(s->phase==SHYT_V408_SOLVING_WORK) {
            uint64_t nonce=0;
            const int ready=shyt_yt_work_poll_v409(s->signup_work,&nonce);
            if(ready!=0) {
                if(ready!=1 ||
                   !shyt_yt_shlk_work_complete_v409(
                       s->auth,s->cookie.data(),s->online_id.c_str(),
                       s->signup_work_bits,nonce)) {
                    // The challenge's actual difficulty is stored below
                    // as work_bits; never fake a work result or skip it.
                    ++s->counters.work_challenges_refused;
                    s->phase=SHYT_V408_WORK_UNSUPPORTED;
                }
                shyt_yt_work_free_v409(s->signup_work);
                s->signup_work=nullptr;
                if(s->phase==SHYT_V408_SOLVING_WORK) {
                    ++s->counters.work_nonces_solved;
                    if(!start_hello(*s,now))return -1;
                }
            }
        }
        if(s->phase==SHYT_V408_LINKED || s->phase==SHYT_V408_QUIET) {
            if((s->counters.heartbeats_sent==0 ||
                maybe_later(now,s->last_ping,kHeartbeat)) &&
               !ping(*s,now)) {
                invalidate_coop(*s);
                s->phase=SHYT_V408_IO_FAILED;
                return -1;
            }
            if(maybe_later(now,s->last_auth_recv,kQuiet)) {
                // Reconnect must re-establish an authoritative world snapshot.
                // Keeping a pre-disconnect CoopStream would trust stale events.
                invalidate_coop(*s);
                s->phase=SHYT_V408_QUIET;
            }
        }
    }catch(...) {
        invalidate_coop(*s);
        s->phase=SHYT_V408_IO_FAILED;
        return -1;
    }
    return 1;
}
extern "C" int shyt_yt_server_phase_v408(
    const ShytYtServerSessionV408* s) {
    return s?s->phase:-1;
}
extern "C" int shyt_yt_server_counters_v408(
    const ShytYtServerSessionV408* s,ShytYtServerCountersV408* out) {
    if(out)*out={};
    if(!s || !out)return 0;
    *out=s->counters;
    return 1;
}
extern "C" int shyt_yt_server_coop_counters_v413(
    const ShytYtServerSessionV408* s,ShytYtCoopCountersV413* out) {
    if(out)*out={};
    if(!s || !out)return 0;
    *out=s->coop_counters;
    return 1;
}
extern "C" int shyt_yt_server_team_observations_v415(
    const ShytYtServerSessionV408* s,ShytYtTeamObservationsV415* out) {
    if(out)*out={};
    if(!s || !out)return 0;
    *out=s->team_observations;
    return 1;
}
extern "C" int shyt_yt_server_take_member_v412(
    ShytYtServerSessionV408* s,ShytYtMemberNoticeV412* out) {
    if(out)*out={};
    if(!s || !out)return 0;
    if(s->member_overflow)return -1;
    if(!s->member_count)return 0;
    *out=s->member_queue[s->member_head];
    s->member_queue[s->member_head]={};
    s->member_head=(s->member_head+1u)%SHYT_V412_MEMBER_QUEUE_CAP;
    --s->member_count;
    return 1;
}
extern "C" int shyt_yt_server_local_port_v408(
    const ShytYtServerSessionV408* s,uint16_t* port_nbo) {
    if(port_nbo)*port_nbo=0;
    return s && s->udp?
        shyt_yt_udp_local_port_v406(s->udp,port_nbo):0;
}
