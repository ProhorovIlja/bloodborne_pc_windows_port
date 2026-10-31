"""V173 original Qt relay: authoritative filtered entries != UDP lost entries."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location(
    "v173",Path(__file__).with_name("stage_policy_route_attribution_v173.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PolicyRouteAttribution(unittest.TestCase):
    def fixture(self):
        h=m.HEADER_OLD+"\n"+m.FIELD_OLD
        hub="void Hub::SomeOtherMethod() {}\n"+m.ROUTED_OLD
        wire=('void LinkServer::ReportWire() {\n'
              '    // YT130_WIRE_TRAFFIC: pinned original socket output\n'
              +m.WIRE_OLD+"\n}\n")
        return h,hub,wire

    def test_original_approved_and_refused_game_routes_are_distinct(self):
        h,hub,wire=m.patch(*self.fixture())
        self.assertEqual(h.count(m.MARKER),1)
        self.assertIn("const RouteAudit previous = m_routeAudit;",h)
        self.assertIn("m_routeAudit = {};",h)
        self.assertEqual(hub.count("++m_routeAudit.allowed_entries;"),1)
        self.assertEqual(hub.count("++m_routeAudit.filtered_entries;"),1)
        self.assertEqual(hub.count("++sender.refused[channel];"),1)
        self.assertEqual(hub.count("packet_routes(sender.endpoint, target.endpoint, channel)"),1)
        self.assertIn('if (channel == 0x05)',hub)
        self.assertIn('if (channel == 0x31)',hub)
        self.assertEqual(wire.count("YT130_ROUTE_POLICY"),1)
        self.assertIn("void LinkServer::ReportWire()",wire)
        # Privacy: log only 4 fixed aggregate counters.
        self.assertNotIn(".online_id",wire)
        self.assertNotIn(".endpoint",wire)
        self.assertNotIn(".ipv4",wire)

    def test_source_edit_drift_and_double_stage_refused(self):
        pristine=self.fixture()
        h,hub,wire=m.patch(*pristine)
        with self.assertRaisesRegex(ValueError,"already staged"):
            m.patch(h,hub,wire)
        with self.assertRaisesRegex(ValueError,"route decision"):
            m.patch(pristine[0],
                    pristine[1].replace("++sender.refused[channel];","++sender.refused[channel + 1];"),
                    pristine[2])
        with self.assertRaisesRegex(ValueError,"V155 source wire staging"):
            m.patch(pristine[0],pristine[1],
                    pristine[2].replace("YT130_WIRE_TRAFFIC","different"))

    def test_no_extra_cost_per_client_or_thrown_packet(self):
        _,hub,_=m.patch(*self.fixture())
        self.assertNotIn("QByteArray",hub)
        self.assertNotIn("push_back",hub)
        self.assertNotIn("append(",hub)
        self.assertNotIn("qInfo",hub)
        self.assertEqual(hub.count("++m_routeAudit."),4)
        self.assertIn("return false;",hub)

if __name__=="__main__":unittest.main()
