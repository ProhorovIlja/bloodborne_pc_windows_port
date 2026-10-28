#!/usr/bin/env python3
"""V100: auto-stage actual mutually consenting YT game pair in original Qt shadNet.

STRICT local-only developer integration, requires SHYT_P2P_TLS_LOCAL_TEST=1
and two operator-pinned distinct client certificates. The real shadNet world
is resolved on the Qt event loop for every attempt; there is no client-supplied
peer, public TLS endpoint, UDP game routing, new process or direct Arm().
"""
from __future__ import annotations

MAIN = "server/src/main.cpp"
MARKER = "SHYT-V100-REAL-GAME-PAIR-AUTOSTAGE-LOCAL-ONLY"


def once(src: str, before: str, after: str, description: str) -> str:
    count = src.count(before)
    if count != 1:
        raise ValueError(f"V100 {description}: expected one pinned anchor, got {count}")
    return src.replace(before, after, 1)


def patch_main(src: str) -> str:
    if MARKER in src:
        raise ValueError("V100 applied twice")
    # Require V78, V79, V81, V90 and the real original-world read-only API.
    for required in (
        'qEnvironmentVariable("SHYT_P2P_TLS_LOCAL_TEST")=="1"',
        'p2p_tls.StartLocal(',
        'const QByteArray cert_pin=qgetenv("SHYT_P2P_TLS_CLIENT_CERT_SHA256");',
        'const QByteArray linked_account=qgetenv("SHYT_P2P_TLS_LINKED_ONLINE_ID");',
        'p2p_tls.ConfigureLocalIdentity(',
        'p2p_tls.ConfigureLocalOfferPeer(',
        'server.CaptureLocalP2POffer(account,selected_peer)',
    ):
        if src.count(required) != 1:
            raise ValueError("V100 needs exact composed original server state: " + required)
    src = once(src, '#include <QDebug>\n',
               '#include <QDebug>\n#include <QTimer> // '+MARKER+'\n',
               "Qt timer include")
    anchor = '''        qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"
'''
    additions = '''        // V100: explicitly enabled TEST of the existing real shadNet world
        // with two distinct operator-pinned mTLS identities. No production
        // listener, no plaintext command and no automatic opt-in.
        const QByteArray second_pin =
            qgetenv("SHYT_P2P_TLS_SECOND_CLIENT_CERT_SHA256");
        const QByteArray second_account =
            qgetenv("SHYT_P2P_TLS_SECOND_LINKED_ONLINE_ID");
        const QByteArray enable_pair = qgetenv("SHYT_P2P_TLS_AUTOPAIR_TEST");
        if ((!enable_pair.isEmpty() && enable_pair!="0" &&
             enable_pair!="1") ||
            (second_pin.isEmpty()!=second_account.isEmpty())) {
            qCritical() << "V100 invalid local-only two-client configuration";
            return 1;
        }
        if (!second_pin.isEmpty() &&
            !p2p_tls.ConfigureLocalIdentity(
                second_pin,second_account,
                [&server](const QByteArray& signed_in_id) {
                    return server.CurrentDirectAccountEpoch(signed_in_id);
                })) {
            qCritical() << "V100 second X509 certificate/game account invalid";
            return 1;
        }
        if (enable_pair=="1") {
            if (cert_pin.isEmpty() || linked_account.isEmpty() ||
                second_pin.isEmpty() || second_account.isEmpty() ||
                linked_account==second_account) {
                qCritical() << "V100 requires two distinct real, pinned players";
                return 1;
            }
            // P2PTlsListener and original game world's session/membership
            // snapshots live on this Qt event loop. Never read from TLS
            // workers or cache old game endpoints after a map/role change.
            auto* pair_clock = new QTimer(&p2p_tls);
            pair_clock->setInterval(1000);
            QObject::connect(pair_clock,&QTimer::timeout,&p2p_tls,
                [&server,&p2p_tls,first=linked_account,second=second_account]() {
                    // ConfigureLocalReciprocalPairV90 refuses to replace a
                    // live outstanding lease; Begin() checks BOTH players'
                    // original authenticated epochs, consent, party, map,
                    // world revision and actual UDP endpoints twice.
                    (void)p2p_tls.ConfigureLocalReciprocalPairV90(
                        first,second,
                        [&server](const QByteArray& recipient,
                                  const QByteArray& peer) {
                            return server.CaptureLocalP2POffer(recipient,peer);
                        });
                });
            pair_clock->start();
        }

'''
    # V102: local-only three-player source-driven team mesh. The three
    # operator pins select test identities, NEVER the peer/client request.
    # Each of 3 pair leases gets independent CSPRNG ID + native ready gate.
    additions += '''        const QByteArray third_pin =
            qgetenv("SHYT_P2P_TLS_THIRD_CLIENT_CERT_SHA256");
        const QByteArray third_account =
            qgetenv("SHYT_P2P_TLS_THIRD_LINKED_ONLINE_ID");
        const QByteArray team_enabled=qgetenv("SHYT_P2P_TLS_AUTOTEAM_TEST");
        if ((!team_enabled.isEmpty() && team_enabled!="0" &&
             team_enabled!="1") ||
            (third_pin.isEmpty()!=third_account.isEmpty()) ||
            (!third_account.isEmpty() &&
             (third_account==linked_account ||
              third_account==second_account))) {
            qCritical() << "V102 invalid third current-game test identity";
            return 1;
        }
        if(!third_pin.isEmpty() &&
           !p2p_tls.ConfigureLocalIdentity(
               third_pin,third_account,
               [&server](const QByteArray& signed_in_id) {
                   return server.CurrentDirectAccountEpoch(signed_in_id);
               })) {
            qCritical() << "V102 third mTLS certificate/game account invalid";
            return 1;
        }
        if(team_enabled=="1") {
            if(cert_pin.isEmpty() || linked_account.isEmpty() ||
               second_pin.isEmpty() || second_account.isEmpty() ||
               third_pin.isEmpty() || third_account.isEmpty() ||
               linked_account==second_account) {
                qCritical() << "V102 requires three distinct pinned real hunters";
                return 1;
            }
            auto* team_clock=new QTimer(&p2p_tls);
            team_clock->setInterval(1000);
            QObject::connect(team_clock,&QTimer::timeout,&p2p_tls,
                [&server,&p2p_tls,a=linked_account,b=second_account,
                 c=third_account]() {
                    // Only original authenticated game parties + both
                    // players' live consent can materialize each edge.
                    // Repeated timer attempts never overwrite valid leases.
                    const auto world_pair=[&server](
                        const QByteArray& recipient,const QByteArray& peer) {
                        return server.CaptureLocalP2POffer(recipient,peer);
                    };
                    std::uint64_t pair_id=0;
                    (void)p2p_tls.ConfigureLocalTeamPairV102(
                        a,b,world_pair,pair_id);
                    (void)p2p_tls.ConfigureLocalTeamPairV102(
                        a,c,world_pair,pair_id);
                    (void)p2p_tls.ConfigureLocalTeamPairV102(
                        b,c,world_pair,pair_id);
                });
            team_clock->start();
        }

'''
    return once(src, anchor, additions + anchor, "local Qt listener insertion")


if __name__ == "__main__":
    raise SystemExit("V100 is a pinned source adapter; invoke through unified compose")
