#!/usr/bin/env python3
"""V88 exact original Qt source injection into server, no public listener."""
import importlib.util
from pathlib import Path
import unittest

folder=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v88patch",folder/"patch_qt_reciprocal_pair_v88.py")
patch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)
DECL="""    std::optional<SeamlessHunt::Hybrid::P2PLocalOfferScope> CaptureLocalP2POffer(
        const QByteArray& tls_recipient,const QByteArray& operator_peer) const;
"""
SOURCES={
 patch.SERVER_H:'#include "sh_p2p_tls_offer_issuer.hpp"\n'+DECL,
 patch.LINK_H:'#include "sh_p2p_tls_offer_issuer.hpp"\n'+DECL,
 patch.SERVER_CPP:"quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {\n",
 patch.LINK_CPP:"quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {\n",
}
class V88Patch(unittest.TestCase):
    def test_real_server_pair_source_and_private_session_scope(self):
        out=patch.patch(SOURCES)
        self.assertEqual(set(out),set(SOURCES))
        self.assertEqual(out[patch.SERVER_H].count(patch.MARKER),1)
        self.assertEqual(out[patch.LINK_H].count(patch.MARKER),1)
        self.assertEqual(out[patch.SERVER_CPP].count("CaptureLocalReciprocalP2POffersV88("),2) # declaration + original LinkServer delegation
        self.assertEqual(out[patch.LINK_CPP].count("CaptureLocalReciprocalP2POffersV88("),1)
        self.assertIn("CaptureLocalP2POffer(first,second)",out[patch.LINK_CPP])
        self.assertIn("CaptureLocalP2POffer(second,first)",out[patch.LINK_CPP])
        self.assertIn("identical(*to_first,*fresh_first)",out[patch.LINK_CPP])
        self.assertIn("identical(*to_second,*fresh_second)",out[patch.LINK_CPP])
        self.assertIn("P2PReciprocalPairIssuerV88::Prepare(",out[patch.LINK_CPP])
        self.assertIn("CryptoDetail::Erase(result.for_a.direction_key)",out[patch.LINK_CPP])
        self.assertNotIn("listen(",out[patch.LINK_CPP])
        self.assertNotIn("DirectReady",out[patch.LINK_CPP])
        with self.assertRaisesRegex(ValueError,"already applied"):
            patch.patch(out)

    def test_pin_sensitive_drift_denied(self):
        for key,value in SOURCES.items():
            altered=dict(SOURCES)
            altered[key]=(value.replace("CaptureLocalP2POffer","CaptureLocalPeerInfo")
                          if key.endswith(".h") else
                          value.replace("CurrentDirectAccountEpoch","ChangedEpoch"))
            with self.subTest(file=key):
                with self.assertRaises(ValueError):
                    patch.patch(altered)
        for key,value in SOURCES.items():
            altered=dict(SOURCES)
            if ".cpp" in key:
                altered[key]=value.replace("CurrentDirectAccountEpoch","Epoch")
            else:
                altered[key]=value.replace("#include \"sh_p2p_tls_offer_issuer.hpp\"\n","")
            with self.subTest(missing=key):
                with self.assertRaises(ValueError):
                    patch.patch(altered)
        with self.assertRaisesRegex(ValueError,"four original"):
            patch.patch({patch.SERVER_H:SOURCES[patch.SERVER_H]})

if __name__=="__main__":
    unittest.main()
