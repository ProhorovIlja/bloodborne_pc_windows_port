#!/usr/bin/env python3
"""V74 real Yharnam Together co-op Hello opt-in and server consent callback.

Patches REAL pinned protobuf, native game world Hello, Qt World/LinkServer and
original Qt tests after V72. Explicit mutual opt-in only; old clients default
false. NO secret/key exchange or automatic Direct transport enablement.
"""
from __future__ import annotations
PROTO="server/coop/coop.proto"
WORLD_H="server/src/bloodborne_world.h"
WORLD_CPP="server/src/bloodborne_world.cpp"
LINK_CPP="server/src/link_server.cpp"
CLIENT_WORLD="emulator/src/core/bloodborne_server_world.cpp"
WORLD_TEST="server/tests/test_bloodborne_world.cpp"

def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise ValueError(f"V74 {label}: expected one pinned anchor, got {n}")
    return s.replace(old,new,1)

def transform(f):
    expected={PROTO,WORLD_H,WORLD_CPP,LINK_CPP,CLIENT_WORLD,WORLD_TEST}
    if set(f)!=expected: raise ValueError("V74 requires all real Qt and client source files")
    p,h,w,l,c,t=(f[x] for x in (PROTO,WORLD_H,WORLD_CPP,LINK_CPP,CLIENT_WORLD,WORLD_TEST))
    if "direct_p2p_opt_in" in p or "PairDirectConsent" in h:
        raise ValueError("V74 already applied")
    p=one(p,
'''    bool enemy_owner = 6;
''',
'''    bool enemy_owner = 6;
    // V74: explicitly consent to exposing this peer's connection endpoint
    // ONLY after a future mutually authenticated encrypted rendezvous.
    // Optional proto3 scalar: legacy clients send no field => false/relay.
    bool direct_p2p_opt_in = 7;
''',"backward compatible game Hello consent field")
    h=one(h,
'''    quint64 DirectWorldEpoch(const ServerLink::Endpoint& from,
                            const ServerLink::Endpoint& to) const;
''',
'''    quint64 DirectWorldEpoch(const ServerLink::Endpoint& from,
                            const ServerLink::Endpoint& to) const;
    // Server-derived opt-in for both CURRENT signed-in account links.
    // Unknown/duplicate/legacy/removed/from another map => DENY.
    bool PairDirectConsent(const QByteArray& a,const QByteArray& b) const;
''',"authoritative mutual consent method")
    h=one(h,
'''        bool enemy_owner = false;
''',
'''        bool enemy_owner = false;
        bool direct_p2p_opt_in = false; // old clients are relay-only
''',"member stores one player's consent")
    w=one(w,
'''void Service::OnHello(Member& member, const bbcoop::Hello& hello, qint64 now_ms, Result& result) {
''',
'''void Service::OnHello(Member& member, const bbcoop::Hello& hello, qint64 now_ms, Result& result) {
    // A refused/replayed/restarted Hello must never preserve an older opt-in.
    member.direct_p2p_opt_in = false;
''',"rehello invalidates old consent")
    w=one(w,
'''    member.enemy_owner = hello.enemy_owner();
''',
'''    member.enemy_owner = hello.enemy_owner();
    // Provenance is the signed-in SHLK link's online_id, not the claimed
    // game board name. This flag alone never creates a direct grant/key.
    member.direct_p2p_opt_in = hello.direct_p2p_opt_in();
''',"new client explicit setting")
    w=one(w,
'''quint64 Service::DirectWorldEpoch(const ServerLink::Endpoint& from,
''',
'''bool Service::PairDirectConsent(const QByteArray& a,const QByteArray& b) const {
    if(a.isEmpty() || b.isEmpty() || a==b) return false;
    const Member* left=nullptr;
    const Member* right=nullptr;
    ServerLink::Endpoint left_endpoint{},right_endpoint{};
    for(const auto& [key,member]:members) {
        if(member.online_id!=a && member.online_id!=b) continue;
        const auto found=endpoints.find(key);
        if(found==endpoints.end()) return false;
        if(member.online_id==a) {
            if(left) return false; // duplicated account identity: deny
            left=&member;left_endpoint=found->second;
        } else {
            if(right) return false;
            right=&member;right_endpoint=found->second;
        }
    }
    if(!left || !right || !left->direct_p2p_opt_in ||
       !right->direct_p2p_opt_in || left->party.isEmpty() ||
       left->party!=right->party)
        return false;
    // This delegates map/team/world/cut/owner checks to the same authority
    // V72 uses for game traffic. No expensive check per game packet.
    return DirectWorldEpoch(left_endpoint,right_endpoint)!=0;
}

quint64 Service::DirectWorldEpoch(const ServerLink::Endpoint& from,
''',"Qt game world is source of peer mutual consent")
    l=one(l,
'''    m_link.SetDirectWorldEpoch([this](const ServerLink::Endpoint& a,
                                      const ServerLink::Endpoint& b) {
        return m_world.DirectWorldEpoch(a,b);
    });
''',
'''    m_link.SetDirectWorldEpoch([this](const ServerLink::Endpoint& a,
                                      const ServerLink::Endpoint& b) {
        return m_world.DirectWorldEpoch(a,b);
    });
    // V74: both players explicitly opt in through their authenticated game
    // Hello. Legacy clients remain relay-only. This callback does NOT send
    // keys/IP addresses, issue a grant or turn on direct game sockets.
    m_link.SetDirectConsent([this](const QByteArray& a,const QByteArray& b) {
        return m_world.PairDirectConsent(a,b);
    });
''',"Qt Hub receives game-world consent")
    c=one(c,
'''            hello.mutable_hello()->set_enemy_owner(enemy_owner_switch);
''',
'''            hello.mutable_hello()->set_enemy_owner(enemy_owner_switch);
            // V74 native-only explicit opt-in. Does NOT enable Direct by
            // itself and never distributes addresses, credentials or keys.
            // The full secure server grant path remains unimplemented.
#ifdef BLOODBORNE_NATIVE_PORT
            const char* native_direct_opt_in=std::getenv("SHYT_DIRECT_P2P_OPT_IN");
            hello.mutable_hello()->set_direct_p2p_opt_in(
                native_direct_opt_in && native_direct_opt_in[0]=='1' &&
                native_direct_opt_in[1]=='\\0');
#endif
''',"native client Hello opt-in, off by default")
    t=one(t,
'''  CHECK(service.DirectWorldEpoch(host.endpoint,guest.endpoint)==0);
''',
'''  CHECK(service.DirectWorldEpoch(host.endpoint,guest.endpoint)==0);
  CHECK(!service.PairDirectConsent("host","guest")); // unknown opt-in
''',"legacy hello opt-in absent")
    t=one(t,
'''  CHECK(current_epoch!=0);
''',
'''  CHECK(current_epoch!=0);
  CHECK(!service.PairDirectConsent("host","guest")); // old co-op clients
''',"legacy current same-map pair remains denied")
    t=one(t,
'''  CHECK(service.DirectWorldEpoch(a.endpoint,b.endpoint)==0);
''',
'''  CHECK(service.DirectWorldEpoch(a.endpoint,b.endpoint)==0);
  CHECK(!service.PairDirectConsent("aa","bb"));
''',"team removal revokes consent")
    return {PROTO:p,WORLD_H:h,WORLD_CPP:w,LINK_CPP:l,CLIENT_WORLD:c,WORLD_TEST:t}
