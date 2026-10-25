#!/usr/bin/env python3
"""V79: local mTLS pinned certificate must match CURRENT signed-in game link.

The fixed BIND probe never returns IPs/keys, and TLS readiness is loopback-
only, disabled by default. Operator provisioning exclusively via root-local
test environment: no user-supplied online_id/CN/SAN can bind a session.
"""
from __future__ import annotations
MAIN="server/src/main.cpp"
SERVER_H="server/src/server.h"
SERVER_CPP="server/src/server.cpp"
LINK_H="server/src/link_server.h"
LINK_CPP="server/src/link_server.cpp"
WORLD_H="server/src/bloodborne_world.h"
WORLD_CPP="server/src/bloodborne_world.cpp"
IDENTITY_H="server/src/sh_p2p_tls_identity.hpp"
def one(src,old,new,label):
    count=src.count(old)
    if count!=1: raise ValueError(f"V79 {label}: {count} pinned anchors")
    return src.replace(old,new,1)
def patch(files):
    paths=(MAIN,SERVER_H,SERVER_CPP,LINK_H,LINK_CPP,WORLD_H,WORLD_CPP)
    if set(files)!=set(paths): raise ValueError("V79 expected original Qt server source tree")
    main,server_h,server_cpp,link_h,link_cpp,world_h,world_cpp=(files[p] for p in paths)
    world_h=one(world_h,
'''    bool PairDirectConsent(const QByteArray& a,const QByteArray& b) const;
''',
'''    bool PairDirectConsent(const QByteArray& a,const QByteArray& b) const;
    // 0 means no current/consenting game. Never trusts TLS certificate CN.
    quint64 CurrentDirectAccountEpoch(const QByteArray& online_id) const;
''',"World API")
    world_cpp=one(world_cpp,
'''bool Service::PairDirectConsent(const QByteArray& a,const QByteArray& b) const {
''',
'''quint64 Service::CurrentDirectAccountEpoch(const QByteArray& id) const {
    if(id.isEmpty())return 0;
    const Member* found=nullptr;
    for(const auto& [key,member]:members) {
        if(member.online_id!=id)continue;
        if(found || endpoints.find(key)==endpoints.end())return 0;
        found=&member;
    }
    if(!found || !found->direct_p2p_opt_in ||
       found->direct_state_serial==0 || found->map==0 ||
       found->party.isEmpty() ||
       (!found->cut_from.isEmpty() && found->cut_from==found->party))
        return 0;
    if(worlds.find(found->party)==worlds.end())return 0;
    return found->direct_state_serial;
}

bool Service::PairDirectConsent(const QByteArray& a,const QByteArray& b) const {
''',"live current game session from server world")
    link_h=one(link_h,
'''    bool Start(const QHostAddress& addr, uint16_t port);
''',
'''    bool Start(const QHostAddress& addr, uint16_t port);
    // Invoked only on TLS BIND, never per game datagram.
    quint64 CurrentDirectAccountEpoch(const QByteArray& id) const;
''',"Qt Link API")
    link_cpp=one(link_cpp,
'''bool LinkServer::SignIn(const QByteArray& online_id, const QByteArray& secret) {
''',
'''quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
    if(!m_signedIn.contains(id))return 0;
    return m_world.CurrentDirectAccountEpoch(id);
}

bool LinkServer::SignIn(const QByteArray& online_id, const QByteArray& secret) {
''',"authenticated game link must be signed-in")
    server_h=one(server_h,
'''    SharedState& Shared() {
''',
'''    quint64 CurrentDirectAccountEpoch(const QByteArray& online_id) const;
    SharedState& Shared() {
''',"expose readonly server-owned identity gate")
    server_cpp=one(server_cpp,
'''ShadNetServer::~ShadNetServer() {
''',
'''quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
    return m_linkServer ? m_linkServer->CurrentDirectAccountEpoch(id) : 0;
}

ShadNetServer::~ShadNetServer() {
''',"same process TLS/world game binding")
    main=one(main,
'''        qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"
''',
'''        // V79 LOCAL TEST ONLY: a privileged operator pins EXACT leaf DER
        // SHA256 to one current account; no CN/SAN/HTTP/SHLK user claim.
        const QByteArray cert_pin=qgetenv("SHYT_P2P_TLS_CLIENT_CERT_SHA256");
        const QByteArray linked_account=qgetenv("SHYT_P2P_TLS_LINKED_ONLINE_ID");
        if(cert_pin.isEmpty()!=linked_account.isEmpty() ||
           (!cert_pin.isEmpty() &&
            !p2p_tls.ConfigureLocalIdentity(
                cert_pin,linked_account,
                [&server](const QByteArray& signed_in_id) {
                    return server.CurrentDirectAccountEpoch(signed_in_id);
                }))) {
            qCritical() << "Invalid local TLS certificate/account pin; no binding";
            return 1;
        }
        qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"
''',"operator fingerprint bound to live SHLK/game account")
    return dict(zip(paths,(main,server_h,server_cpp,link_h,link_cpp,world_h,world_cpp)))
