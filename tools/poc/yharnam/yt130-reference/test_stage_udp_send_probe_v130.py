"""V130 original Qt UDP write diagnostic guards. Never a QoS pass claim."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest
import stage_wire_traffic as wire

spec=importlib.util.spec_from_file_location(
    "yt130_udp_v130",Path(__file__).with_name("stage_udp_send_probe_v130.py"))
assert spec is not None and spec.loader is not None
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class SendMetricsTests(unittest.TestCase):
    def setUp(self):
        self.cpp="\n".join((mod.HUB_OLD,mod.WORLD_OLD,mod.CPP_ANCHOR,mod.LOG_OLD))
        self.header="\n".join((mod.H_ANCHOR,mod.FIELD_ANCHOR))
    def test_two_unchanged_send_paths_and_single_qt_thread_report(self):
        cpp,h=mod.rewrite(self.cpp,self.header)
        self.assertEqual(cpp.count("SendMeasured(send.datagram,"),1)
        self.assertEqual(cpp.count("SendMeasured(*sealed,"),1)
        self.assertEqual(cpp.count("m_socket->writeDatagram(datagram, QHostAddress(ipv4), port)"),1)
        self.assertEqual(cpp.count("RecordWire(datagram, false);"),1)
        self.assertIn("YT130_SEND_PROBE calls=",cpp)
        self.assertIn("max_pending_bytes=",cpp)
        self.assertIn("m_diagSendErrors = m_diagSendBusyUs = m_diagSendMaxUs = 0;",cpp)
        self.assertIn("quint64 m_diagSendErrors = 0;",h)
        self.assertEqual(cpp.count("for (const auto& send : result.sends)"),2)
        self.assertNotIn("drop",mod.HUB_NEW.lower()+mod.WORLD_NEW.lower())
    def test_upstream_1_3_0_wire_source_is_expected(self):
        self.assertEqual(wire.PIN,mod.PIN)
        self.assertEqual(wire.PATCHES_CPP[2][1].count(mod.HUB_OLD),1)
        self.assertEqual(wire.PATCHES_CPP[3][1].count(mod.WORLD_OLD),1)
        self.assertIn(mod.LOG_OLD,wire.PATCHES_CPP[1][1])
    def test_no_pii_in_metrics_and_source_drift_fails_closed(self):
        cpp,h=mod.rewrite(self.cpp,self.header)
        for sensitive in ("online_id","secret","member","payload","source_addr","ip_text"):
            self.assertNotIn(sensitive,mod.LOG_NEW)
        with self.assertRaises(ValueError):mod.rewrite(cpp,h)
        with self.assertRaises(ValueError):mod.rewrite(self.cpp.replace(mod.HUB_OLD,"BROKEN"),self.header)
        with self.assertRaises(ValueError):mod.rewrite(self.cpp,self.header.replace(mod.FIELD_ANCHOR,"BROKEN"))


if __name__=="__main__":unittest.main()
