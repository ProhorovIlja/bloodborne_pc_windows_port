#!/usr/bin/env python3
"""V81: one-time sealed peer offer within the existing loopback Qt mTLS daemon.

Original server-owned authenticated game pair/consent/world state ONLY.
Never creates an Internet listener, a separate game server, or SHLK secrets.
"""
from __future__ import annotations

MAIN="server/src/main.cpp"
SERVER_H="server/src/server.h"
SERVER_CPP="server/src/server.cpp"
LINK_H="server/src/link_server.h"
LINK_CPP="server/src/link_server.cpp"
CMAKE="server/CMakeLists.txt"
OFFER_H="server/src/sh_p2p_tls_offer_issuer.hpp"
def one(src,old,new,label):
    n=src.count(old)
    if n!=1: raise ValueError(f"V81 {label}: pinned original Qt server mismatch ({n})")
    return src.replace(old,new,1)
def patch(files):
    paths=(MAIN,SERVER_H,SERVER_CPP,LINK_H,LINK_CPP)
    if set(files)!=set(paths):raise ValueError("V81 needs the exact real Qt server/main source")
    main,sh,sc,lh,lc=(files[p] for p in paths)
    if "CaptureLocalP2POffer" in sh: raise ValueError("V81 repeated")
    sh=one(sh,
'''    quint64 CurrentDirectAccountEpoch(const QByteArray& online_id) const;
''',
'''    quint64 CurrentDirectAccountEpoch(const QByteArray& online_id) const;
    std::optional<SeamlessHunt::Hybrid::P2PLocalOfferScope> CaptureLocalP2POffer(
        const QByteArray& tls_recipient,const QByteArray& operator_peer) const;
''',"same Qt server public readonly snapshot API")
    sh=one(sh,
'''#include "link_server.h"
''',
'''#include "link_server.h"
#include "sh_p2p_tls_offer_issuer.hpp"
''',"offer types in Qt server")
    sc=one(sc,
'''quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
''',
'''std::optional<SeamlessHunt::Hybrid::P2PLocalOfferScope>
ShadNetServer::CaptureLocalP2POffer(
    const QByteArray& recipient,const QByteArray& peer) const {
    if(!m_linkServer)return std::nullopt;
    return m_linkServer->CaptureLocalP2POffer(recipient,peer);
}

quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
''',"offer delegation in actual ShadNetServer")
    lh=one(lh,
'''    quint64 CurrentDirectAccountEpoch(const QByteArray& id) const;
''',
'''    quint64 CurrentDirectAccountEpoch(const QByteArray& id) const;
    std::optional<SeamlessHunt::Hybrid::P2PLocalOfferScope> CaptureLocalP2POffer(
        const QByteArray& tls_recipient,const QByteArray& operator_peer) const;
''',"game link readonly offer scope")
    lh=one(lh,
'''#include "server_link.h"
''',
'''#include "server_link.h"
#include "sh_p2p_tls_offer_issuer.hpp"
''',"include secured scope type")
    lc=one(lc,
'''quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
''',
'''std::optional<SeamlessHunt::Hybrid::P2PLocalOfferScope>
LinkServer::CaptureLocalP2POffer(
    const QByteArray& recipient,const QByteArray& peer) const {
    if(recipient.isEmpty() || peer.isEmpty() || recipient==peer ||
       !m_signedIn.contains(recipient) || !m_signedIn.contains(peer))
        return std::nullopt;
    const quint64 requester_epoch=m_world.CurrentDirectAccountEpoch(recipient);
    const quint64 peer_epoch=m_world.CurrentDirectAccountEpoch(peer);
    if(!requester_epoch || !peer_epoch)return std::nullopt;
    const auto snapshot=m_world.CaptureDirectPairScope(recipient,peer);
    if(!snapshot ||
       snapshot->first_account!=recipient || snapshot->second_account!=peer ||
       snapshot->world_revision==0)return std::nullopt;
    const auto& real=snapshot->second_physical;
    const auto& virtual_peer=snapshot->second_virtual;
    if(!real.ipv4 || !real.port || !virtual_peer.ipv4 || !virtual_peer.port)
        return std::nullopt;
    // All values from the authenticated server-side current game/SHLK
    // links, never from cert common name or TLS client-provided peer ID.
    return SeamlessHunt::Hybrid::P2PLocalOfferScope{
        recipient,peer,requester_epoch,peer_epoch,snapshot->world_revision,
        real.ipv4,real.port,virtual_peer.ipv4,virtual_peer.port};
}

quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
''',"derive full offer source ONLY from signed-in session and both consents")
    main=one(main,
'''        qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"
''',
'''        // V81: optional LOCAL OPERATOR-SELECTED peer. No arbitrary client
        // string can select an account or disclose a real peer endpoint.
        // Runtime TLS listener still binds only 127.0.0.1 and is OFF by default.
        const QByteArray peer=qgetenv("SHYT_P2P_TLS_OFFER_PEER_ID");
        if(!peer.isEmpty() &&
           !p2p_tls.ConfigureLocalOfferPeer(peer,
               [&server](const QByteArray& account,const QByteArray& selected_peer) {
                   return server.CaptureLocalP2POffer(account,selected_peer);
               })) {
            qCritical() << "Invalid V81 local offer peer";
            return 1;
        }
        qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"
''',"operator-selected test-only peer and authoritative Qt snapshot")
    return dict(zip(paths,(main,sh,sc,lh,lc)))

def patch_cmake(original):
    if "V81_AES_GCM_CRYPTO_LINK" in original:
        raise ValueError("V81 CMake already patched")
    return one(original,
'''target_link_libraries(shadnet PRIVATE
    Qt6::Core
''',
'''# V81_AES_GCM_CRYPTO_LINK: same Qt process, V75 SHG1 AES-GCM
# implementation uses OpenSSL EVP on Linux; Windows uses native CNG.
if(WIN32)
    set(SHYT_V81_CRYPTO_BACKEND bcrypt)
else()
    find_package(OpenSSL REQUIRED COMPONENTS Crypto)
    set(SHYT_V81_CRYPTO_BACKEND OpenSSL::Crypto)
endif()
target_link_libraries(shadnet PRIVATE
    ${SHYT_V81_CRYPTO_BACKEND}
    Qt6::Core
''',"link actual Qt shadNet to platform AES GCM backend")

