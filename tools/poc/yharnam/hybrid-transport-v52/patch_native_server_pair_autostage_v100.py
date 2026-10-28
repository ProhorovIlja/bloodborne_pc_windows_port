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
    return once(src, anchor, additions + anchor, "local Qt listener insertion")


if __name__ == "__main__":
    raise SystemExit("V100 is a pinned source adapter; invoke through unified compose")
