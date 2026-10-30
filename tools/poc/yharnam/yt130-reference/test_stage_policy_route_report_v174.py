"""V174: preserve only genuine original Qt intentionally refused route counts."""
import importlib.util
import os
from pathlib import Path
import re
import tempfile
from textwrap import dedent
import unittest

spec=importlib.util.spec_from_file_location(
    "yt174",Path(__file__).with_name("stage_policy_route_report_v174.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PolicyJson(unittest.TestCase):
    def fixture(self):
        return ("\n".join([
            "# SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE",
            "# SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS",
            "# SHYT_V169_SYNTHETIC_DIRECTED_GAME_COHORT",
            m.OLD_BEGIN,m.OLD_ROW,m.OLD_TOTAL]))
    def test_exact_source_and_doubled_source_refused(self):
        p=m.patch(self.fixture())
        self.assertIn(m.MARK,p)
        self.assertIn("policy_pattern.search(line)",p)
        self.assertIn('"game_policy_filtered_enemy_hp_05":',p)
        self.assertIn("NOT same as V161 source-clock cohort",p)
        with self.assertRaisesRegex(ValueError,"drift"):
            m.patch(p)
        with self.assertRaisesRegex(ValueError,"requires staged"):
            m.patch(self.fixture().replace(
                "SHYT_V169_SYNTHETIC_DIRECTED_GAME_COHORT","missing"))
    def test_real_log_parser_counts_per_shard_and_rejects_impossible_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"shard0"/"shadnet.log"
            path.parent.mkdir()
            path.write_text(
                "QT first YT130_ROUTE_POLICY allowed_entries=200 filtered_entries=40 "
                "filtered_enemy_hp_05=39 filtered_event_sync_31=1\n"
                "YT130_ROUTE_POLICY allowed_entries=90 filtered_entries=7 "
                "filtered_enemy_hp_05=7 filtered_event_sync_31=0\n"
                "OTHER player names ignored (no export)\n",encoding="utf-8")
            pre=m.NEW_BEGIN.split("        per_shard = []")[0]
            ns={"re":re,"os":os,"root":tmp}
            exec(dedent(pre),ns)
            self.assertEqual(ns["route_policy"](0),(290,47,46,1,2))
            path.write_text(
                "YT130_ROUTE_POLICY allowed_entries=2 filtered_entries=1 "
                "filtered_enemy_hp_05=2 filtered_event_sync_31=0\n",
                encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError,"inconsistent"):
                ns["route_policy"](0)
    def test_reports_are_non_identity_and_do_not_change_qos_gate(self):
        out=m.patch(self.fixture())
        self.assertNotIn('"online_id"',out)
        self.assertNotIn('"ipv4"',out)
        self.assertNotIn('"packet_payload"',out)
        self.assertNotIn('cohort_quality =',out)
        self.assertNotIn('directed_quality =',out)

if __name__=="__main__":unittest.main()
