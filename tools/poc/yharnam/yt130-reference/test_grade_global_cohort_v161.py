"""V161: authenticated-Qt loadtest stays RED on historical 85% delivery even
if common packet timestamp cohort scores 99%. Fail closed on invalid evidence.
"""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent

def import_file(name,tag):
    spec=importlib.util.spec_from_file_location(tag,HERE/name)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

grade=import_file("run_five_hunter_shards_v117.py","yt161_grade")
cases=import_file("test_shard_five_v117.py","yt161_cases")

def with_cohort(s):
    s=dict(s)
    s.update(
        cohort_quality="GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY",
        cohort_start_us=18_000_000,cohort_end_us=28_000_000,
        cohort_seconds=10,cohort_packets_sent=20000,
        cohort_packets_received=19820,
        cohort_scope="shared monotonic send-timestamp whole buckets, after all bbload teams Playing; NOT a production QoS pass")
    return s

class SourceVerifiedGlobalQosV161(unittest.TestCase):
    def test_healthy_cohort_does_not_erase_old_original_qa_red(self):
        for shards in (1,3):
            src=with_cohort(cases.sample(shards))
            result=grade.grade(src,shards)
            self.assertEqual(result["quality"],"FULL_GAMEPLAY_SYNTHETIC_ONLY")
            self.assertEqual(result["cohort_quality"],
                             "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY")
            src["steady_packets_received"]=10000
            result=grade.grade(src,shards)
            self.assertEqual(result["quality"],"STEADY_DELIVERY_DEGRADED")
            self.assertEqual(result["cohort_quality"],
                             "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY")
            src["packets_lost"]=55
            result=grade.grade(src,shards)
            self.assertEqual(result["quality"],"REAL_GAME_DELIVERY_DEGRADED")
    def test_invalid_missing_partial_false_green_is_rejected(self):
        base=with_cohort(cases.sample(1))
        for key in ("cohort_quality","cohort_start_us","cohort_end_us",
                    "cohort_seconds","cohort_packets_sent",
                    "cohort_packets_received","cohort_scope"):
            with self.subTest(field=key):
                s=dict(base)
                s.pop(key)
                self.assertEqual(grade.grade(s,1)["quality"],
                                 "MISSING_OR_PARTIAL_GLOBAL_COHORT_EVIDENCE")
        for key,value in [
            ("cohort_quality","HACKED_SUCCESS"),
            ("cohort_packets_sent",-2),
            ("cohort_packets_received",True),
            ("cohort_end_us",20_000_000),
            ("cohort_packets_received",19000),
            ("cohort_seconds",4),
            ("cohort_scope","production pass"),
        ]:
            with self.subTest(field=key):
                s=dict(base)
                s[key]=value
                self.assertEqual(grade.grade(s,1)["quality"],
                                 "INVALID_GLOBAL_COHORT_EVIDENCE")
    def test_200_player_health_requires_all_800_anonymous_directed_routes(self):
        sample=with_cohort(cases.sample(1))
        self.assertEqual(grade.grade(sample,1,require_directed=True)["quality"],
                         "MISSING_REQUIRED_DIRECTED_GAME_EVIDENCE")
        sample.update(directed_quality="DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY",
                      directed_packets_sent=20000,directed_packets_received=19820,
                      directed_routes=800,
                      directed_scope="anonymous synthetic seat pairs; NOT a production QoS pass")
        good=grade.grade(sample,1,require_directed=True)
        self.assertEqual(good["quality"],"FULL_GAMEPLAY_SYNTHETIC_ONLY")
        self.assertEqual(good["directed_routes"],800)
        sample["directed_quality"]="DIRECTED_GAME_COHORT_DELIVERY_DEGRADED"
        self.assertEqual(grade.grade(sample,1,require_directed=True)["quality"],
                         "DIRECTED_GAME_COHORT_UNHEALTHY")
        sample["directed_quality"]="DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY"
        for key,value in (("directed_routes",799),
                          ("directed_packets_received",19819),
                          ("directed_scope","production pass")):
            with self.subTest(field=key):
                damaged=dict(sample)
                damaged[key]=value
                self.assertEqual(grade.grade(damaged,1,require_directed=True)["quality"],
                                 "INVALID_DIRECTED_GAME_EVIDENCE")
        missing=dict(sample)
        missing.pop("directed_packets_received")
        self.assertEqual(grade.grade(missing,1,require_directed=True)["quality"],
                         "MISSING_OR_PARTIAL_DIRECTED_GAME_EVIDENCE")

    def test_valid_cohort_red_remains_red(self):
        s=with_cohort(cases.sample(1))
        s["cohort_quality"]="GLOBAL_GAME_COHORT_DELIVERY_DEGRADED"
        s["cohort_packets_received"]=15000
        result=grade.grade(s,1)
        self.assertEqual(result["cohort_quality"],
                         "GLOBAL_GAME_COHORT_DELIVERY_DEGRADED")
        self.assertEqual(result["quality"],"FULL_GAMEPLAY_SYNTHETIC_ONLY")

if __name__=="__main__":
    unittest.main()
