#!/usr/bin/env python3
"""V100 guarded original-server local-only auto pair source regressions."""
import importlib.util
from pathlib import Path
import unittest

directory = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "shyt_v100", directory/"patch_native_server_pair_autostage_v100.py")
v100 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v100)

SOURCE = '''#include <QDebug>
    if (qEnvironmentVariable("SHYT_P2P_TLS_LOCAL_TEST")=="1") {
        if (!p2p_tls.StartLocal("server.pem","server.key","ca.pem",0))
            return 1;
        const QByteArray cert_pin=qgetenv("SHYT_P2P_TLS_CLIENT_CERT_SHA256");
        const QByteArray linked_account=qgetenv("SHYT_P2P_TLS_LINKED_ONLINE_ID");
        if (!p2p_tls.ConfigureLocalIdentity(cert_pin,linked_account,identity))
            return 1;
        p2p_tls.ConfigureLocalOfferPeer("peer",
            [&server](const QByteArray& account,const QByteArray& selected_peer) {
                return server.CaptureLocalP2POffer(account,selected_peer);
            });
        qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"
                << p2p_tls.serverPort();
    }
'''

class V100Tests(unittest.TestCase):
    def test_actual_qt_game_world_and_two_identity_only(self):
        transformed = v100.patch_main(SOURCE)
        self.assertEqual(transformed.count(v100.MARKER),1)
        self.assertIn('#include <QTimer>',transformed)
        self.assertIn('SHYT_P2P_TLS_SECOND_CLIENT_CERT_SHA256',transformed)
        self.assertIn('SHYT_P2P_TLS_SECOND_LINKED_ONLINE_ID',transformed)
        self.assertIn('SHYT_P2P_TLS_AUTOPAIR_TEST',transformed)
        self.assertIn('second_pin.isEmpty()!=second_account.isEmpty()',transformed)
        self.assertIn('linked_account==second_account',transformed)
        self.assertIn('p2p_tls.ConfigureLocalIdentity(',transformed)
        self.assertIn('new QTimer(&p2p_tls)',transformed)
        self.assertIn('QObject::connect(pair_clock,&QTimer::timeout,&p2p_tls,',transformed)
        self.assertIn('p2p_tls.ConfigureLocalReciprocalPairV90(',transformed)
        self.assertIn('server.CaptureLocalP2POffer(recipient,peer)',transformed)
        self.assertIn('pair_clock->start();',transformed)
        self.assertLess(transformed.index('if (enable_pair=="1")'),
                        transformed.index('p2p_tls.ConfigureLocalReciprocalPairV90('))
        self.assertLess(transformed.index('p2p_tls.StartLocal('),
                        transformed.index('new QTimer(&p2p_tls)'))
        self.assertEqual(transformed.count('p2p_tls.StartLocal('),1)
        self.assertNotIn('direct_ingress.Arm(',transformed)
        self.assertNotIn('direct_egress.Arm(',transformed)
        self.assertNotIn('listen(QHostAddress::Any',transformed)
        self.assertNotIn('SHYT_P2P_TLS_PUBLIC',transformed)
        with self.assertRaisesRegex(ValueError,"applied twice"):
            v100.patch_main(transformed)

    def test_drift_fails_closed(self):
        invalid=[
            SOURCE.replace('p2p_tls.StartLocal(','StartWithoutTls('),
            SOURCE.replace('SHYT_P2P_TLS_LOCAL_TEST','SHYT_P2P_PUBLIC_TEST'),
            SOURCE.replace('p2p_tls.ConfigureLocalIdentity(','NoCertBinding('),
            SOURCE.replace('p2p_tls.ConfigureLocalOfferPeer(','NoLiveWorld('),
            SOURCE.replace('server.CaptureLocalP2POffer(account,selected_peer)',
                           'TrustClientSubmittedEndpoint(account,selected_peer)'),
            SOURCE.replace('#include <QDebug>','#include <QWidget>'),
            SOURCE.replace('SHYT_P2P_TLS_LINKED_ONLINE_ID','CLIENT_CLAIMED_ID'),
            SOURCE.replace('qInfo() << "Local-only mTLS P2P readiness check on 127.0.0.1:"',
                           'qInfo() << "Internet P2P server:"'),
        ]
        for index,s in enumerate(invalid):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    v100.patch_main(s)

if __name__ == "__main__":
    unittest.main()
