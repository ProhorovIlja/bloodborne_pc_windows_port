#!/usr/bin/env python3
"""V88: original single Qt shadNet server can mint reciprocal SHG2 grants.

The two captures are read-only original signed-in LinkServer snapshots,
including BOTH players' mutual consent, map/world/epoch and routes.
All original server code anchors and revalidation fail closed.
It neither changes the V85 TLS listener nor enables actual Direct UDP.
"""
from __future__ import annotations

SERVER_H="server/src/server.h"
SERVER_CPP="server/src/server.cpp"
LINK_H="server/src/link_server.h"
LINK_CPP="server/src/link_server.cpp"
HEADER="server/src/sh_p2p_reciprocal_pair_v88.hpp"
MARKER="SHYT-V88-RECIPROCAL-ORIGINAL-LINK"

def one(s,old,new,why):
    n=s.count(old)
    if n!=1: raise ValueError(f"V88 {why}: pinned Qt source drift: {n}")
    return s.replace(old,new,1)

DECL="""    std::optional<SeamlessHunt::Hybrid::P2PReciprocalOffersV88>
    CaptureLocalReciprocalP2POffersV88(
        const QByteArray& first,const QByteArray& second) const;
"""

def patch(paths):
    names=(SERVER_H,SERVER_CPP,LINK_H,LINK_CPP)
    if set(paths)!=set(names):
        raise ValueError("V88 requires four original composed Qt server sources")
    sh,sc,lh,lc=(paths[p] for p in names)
    if any(MARKER in t or "CaptureLocalReciprocalP2POffersV88" in t
           for t in (sh,sc,lh,lc)):
        raise ValueError("V88 already applied")
    sh=one(sh,
        '#include "sh_p2p_tls_offer_issuer.hpp"\n',
        '#include "sh_p2p_tls_offer_issuer.hpp"\n'
        '#include "sh_p2p_reciprocal_pair_v88.hpp" // '+MARKER+'\n',
        "ShadNetServer reciprocal type")
    lh=one(lh,
        '#include "sh_p2p_tls_offer_issuer.hpp"\n',
        '#include "sh_p2p_tls_offer_issuer.hpp"\n'
        '#include "sh_p2p_reciprocal_pair_v88.hpp" // '+MARKER+'\n',
        "LinkServer reciprocal type")
    existing="""    std::optional<SeamlessHunt::Hybrid::P2PLocalOfferScope> CaptureLocalP2POffer(
        const QByteArray& tls_recipient,const QByteArray& operator_peer) const;
"""
    sh=one(sh,existing,existing+DECL,"ShadNetServer typed public internal API")
    lh=one(lh,existing,existing+DECL,"LinkServer typed public internal API")
    sc=one(sc,
        """quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
""",
        """std::optional<SeamlessHunt::Hybrid::P2PReciprocalOffersV88>
ShadNetServer::CaptureLocalReciprocalP2POffersV88(
    const QByteArray& first,const QByteArray& second) const {
    // This is not an unauthenticated HTTP/TLS endpoint. Only a trusted
    // internal server caller may choose accounts; no game packet route.
    if(!m_linkServer)return std::nullopt;
    return m_linkServer->CaptureLocalReciprocalP2POffersV88(first,second);
}

quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
""",
        "original shadNet single-process delegation")
    lc=one(lc,
        """quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
""",
        """std::optional<SeamlessHunt::Hybrid::P2PReciprocalOffersV88>
LinkServer::CaptureLocalReciprocalP2POffersV88(
    const QByteArray& first,const QByteArray& second) const {
    // Server authoritative source ONLY: original signed-in sessions
    // and both players' current map/team consent, captured in BOTH
    // directions. This executes synchronously in the original Qt event
    // loop; it is not a durable lease nor an independent public API.
    if(first.isEmpty() || second.isEmpty() || first==second)
        return std::nullopt;
    const auto to_first=CaptureLocalP2POffer(first,second);
    const auto to_second=CaptureLocalP2POffer(second,first);
    if(!to_first || !to_second)return std::nullopt;
    const qint64 timestamp=QDateTime::currentMSecsSinceEpoch();
    if(timestamp<=0)return std::nullopt;
    SeamlessHunt::Hybrid::P2PReciprocalOffersV88 result{};
    if(!SeamlessHunt::Hybrid::P2PReciprocalPairIssuerV88::Prepare(
          *to_first,*to_second,static_cast<std::uint64_t>(timestamp),
          result.for_a,result.for_b))return std::nullopt;
    // No yield/network call while minting; double-read both server
    // directions before releasing any secrets. Any state drift denies.
    const auto fresh_first=CaptureLocalP2POffer(first,second);
    const auto fresh_second=CaptureLocalP2POffer(second,first);
    const auto identical=[](const SeamlessHunt::Hybrid::P2PLocalOfferScope& a,
                            const SeamlessHunt::Hybrid::P2PLocalOfferScope& b) {
        return a.recipient==b.recipient && a.peer==b.peer &&
            a.recipient_epoch==b.recipient_epoch &&
            a.peer_epoch==b.peer_epoch &&
            a.world_revision==b.world_revision &&
            a.physical_ipv4_host==b.physical_ipv4_host &&
            a.physical_port_host==b.physical_port_host &&
            a.virtual_ipv4_host==b.virtual_ipv4_host &&
            a.virtual_port_host==b.virtual_port_host;
    };
    if(!fresh_first || !fresh_second ||
       !identical(*to_first,*fresh_first) ||
       !identical(*to_second,*fresh_second)) {
        SeamlessHunt::Hybrid::CryptoDetail::Erase(result.for_a.direction_key);
        SeamlessHunt::Hybrid::CryptoDetail::Erase(result.for_b.direction_key);
        return std::nullopt;
    }
    return result;
}

quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
""",
        "original session and world reciprocal grant capture")
    return dict(zip(names,(sh,sc,lh,lc)))
