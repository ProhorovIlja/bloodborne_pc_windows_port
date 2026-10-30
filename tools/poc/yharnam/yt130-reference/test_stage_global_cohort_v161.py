"""V161: all 5-hunter bbload workers use one sender timestamp cohort."""
import importlib.util
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace
import unittest

p=Path(__file__).with_name("stage_global_cohort_v161.py")
spec=importlib.util.spec_from_file_location("yt_v161_global",p)
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def original_bbload_fixture():
    return (
        "#include <QHostAddress>\n"
        "SHYT_V158_NATIVE_QT_RECEIVE_DIAGNOSTICS\n"
        "SHYT_V159_ORIGINAL_TEAM_LOBBY_REFUSAL_DETAIL\n"+
        v.CLASS_OLD+v.SENT_OLD+v.RECEIVED_OLD+v.FINISH_OLD
    )

def original_shard_fixture():
    return (
        "# SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE\n"
        '"game_frame_decoded": sum(r["game_frame_decoded"] for r in results),\n'
        '"team_unknown_other": sum(r["team_unknown_other"] for r in results),\n'
        +v.ANCHOR_AGG+v.SUMMARY_OLD
    )

def worker(ready,finish,counts,playing=5):
    return {
        "games":5,"playing":playing,"complete_teams":1 if playing==5 else 0,
        "cohort_ready_us":ready,"cohort_finish_us":finish,
        "cohort_epoch_entries":[{"start_us":second*1_000_000,
            "sent_entries":sent,"received_entries":recv}
            for second,(sent,recv) in counts.items()],
    }

def inspect(results):
    # The patch is inserted at 8-space indentation inside run_shards.py.
    # Standalone exec must dedent it; shards=0 avoids a wire-log dependency
    # while exercising the complete injected aggregation code.
    namespace={"results":results,"args":SimpleNamespace(team_size=5,shards=0)}
    exec(dedent(v.PATCH_AGG),namespace)
    return namespace

class GlobalCohortV161(unittest.TestCase):
    def test_pinned_original_qt_source_guards_and_current_original_coop_kept(self):
        self.assertEqual(v.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(v.BB,"server/loadtest/bbload.cpp")
        staged=v.patch_bbload(original_bbload_fixture())
        self.assertIn(v.MARK,staged)
        self.assertIn("std::map<s64, std::pair<quint64, quint64>>",staged)
        self.assertIn("static_cast<s64>(sent) / 1'000'000",staged)
        self.assertIn("(now_us / 1'000'000)",staged)
        self.assertIn("steady_since_us",staged)
        self.assertIn("cohort_ready_us",staged)
        self.assertIn("cohort_finish_us",staged)
        self.assertEqual(staged.count("QJsonArray cohort_json;"),1)
        self.assertNotIn("member.id()",v.PATCH_AGG)
        self.assertNotIn("name=",v.PATCH_AGG)
        self.assertNotIn("ip=",v.PATCH_AGG)
        with self.assertRaisesRegex(ValueError,"drift"):
            v.patch_bbload(staged)
        with self.assertRaisesRegex(ValueError,"requires staged"):
            v.patch_bbload(original_bbload_fixture().replace(
                "SHYT_V158_NATIVE_QT_RECEIVE_DIAGNOSTICS","not yet"))
        for a in (v.CLASS_OLD,v.SENT_OLD,v.RECEIVED_OLD,v.FINISH_OLD):
            with self.subTest(anchor=a[:30]):
                with self.assertRaises(ValueError):
                    v.patch_bbload(original_bbload_fixture().replace(a,"drift"))
    def test_run_shards_source_pinned_and_emit_is_separate_qos_metric(self):
        s=v.patch_shards(original_shard_fixture())
        self.assertIn('"cohort_packets_received": cohort_received',s)
        self.assertIn('"per_shard": per_shard',s)
        self.assertNotIn("packets_lost",v.PATCH_AGG)
        self.assertNotIn("steady_packets_received",v.PATCH_AGG)
        with self.assertRaises(ValueError):
            v.patch_shards(s)
    def test_different_worker_readiness_never_creates_false_loss(self):
        # 1st worker arms 5 seconds earlier; mismatched V120 would count
        # early sent entries while the receiver has not yet armed.
        complete={s:(400,398) for s in range(12,45)}
        a=worker(12_000_000,47_000_000,complete)
        b=worker(17_300_000,47_000_000,complete)
        out=inspect([a,b])
        self.assertEqual(out["cohort_start_us"],18_000_000)
        self.assertEqual(out["cohort_end_us"],45_000_000)
        self.assertEqual(out["cohort_seconds"],27)
        self.assertEqual(out["cohort_sent"],27*2*400)
        self.assertEqual(out["cohort_received"],27*2*398)
        self.assertEqual(out["cohort_quality"],"GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY")
    def test_actual_global_loss_remains_red(self):
        gaps={s:(400,300) for s in range(20,44)}
        o=inspect([worker(20_000_000,46_000_000,gaps),
                   worker(20_000_000,46_000_000,gaps)])
        self.assertEqual(o["cohort_quality"],"GLOBAL_GAME_COHORT_DELIVERY_DEGRADED")
        self.assertEqual(o["cohort_sent"],24*2*400)
    def test_incomplete_team_or_insufficient_window_fails_closed(self):
        data={s:(500,500) for s in range(10,20)}
        o=inspect([worker(10_000_000,20_000_000,data),
                   worker(11_000_000,20_000_000,data,playing=4)])
        self.assertEqual(o["cohort_quality"],"NO_GLOBAL_200_PLAYER_FIVE_SEAT_COHORT")
        o=inspect([worker(14_900_000,20_000_000,data),
                   worker(14_800_000,20_000_000,data)])
        self.assertEqual(o["cohort_seconds"],3)
        self.assertEqual(o["cohort_quality"],"NO_GLOBAL_200_PLAYER_FIVE_SEAT_COHORT")
    def test_silent_worker_cannot_borrow_healthy_workers_global_qos(self):
        # A worker with 5 games Playing but no actual packets must not
        # disappear inside the sum of the other workers' healthy traffic.
        data={sec:(400,400) for sec in range(10,40)}
        healthy=worker(12_000_000,42_000_000,data)
        silent=worker(12_000_000,42_000_000,{sec:(0,0) for sec in range(10,40)})
        out=inspect([healthy,silent])
        self.assertGreater(out["cohort_sent"],10_000)
        self.assertEqual(out["cohort_quality"],"INVALID_GLOBAL_COHORT_BUCKETS")
        # Sending without receiving, or receiving without sending, also
        # means at least one 5-seat worker has lost its game traffic.
        for sent,recv in ((400,0),(0,400)):
            with self.subTest(sent=sent,received=recv):
                incomplete=worker(12_000_000,42_000_000,
                                  {sec:(sent,recv) for sec in range(10,40)})
                self.assertEqual(inspect([healthy,incomplete])["cohort_quality"],
                                 "INVALID_GLOBAL_COHORT_BUCKETS")
        self.assertEqual(inspect([healthy,healthy])["cohort_quality"],
                         "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY")

    def test_every_worker_must_have_game_packets_in_every_scored_second(self):
        # The other worker's very large healthy sample must never hide
        # a 5-seat worker that stops sending or receiving mid-measurement.
        strong={sec:(10_000,10_000) for sec in range(10,40)}
        weak={sec:(20,20) for sec in range(10,40)}
        a=worker(12_000_000,42_000_000,strong)
        b=worker(12_000_000,42_000_000,weak)
        self.assertEqual(inspect([a,b])["cohort_quality"],
                         "GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY")
        missing=worker(12_000_000,42_000_000,
                       {sec:pair for sec,pair in weak.items() if sec!=23})
        self.assertEqual(inspect([a,missing])["cohort_quality"],
                         "INVALID_GLOBAL_COHORT_BUCKETS")
        for sent,recv in ((0,0),(20,0),(0,20)):
            with self.subTest(sent=sent,received=recv):
                intermittent=dict(weak)
                intermittent[23]=(sent,recv)
                out=inspect([a,worker(12_000_000,42_000_000,intermittent)])
                self.assertEqual(out["cohort_quality"],"INVALID_GLOBAL_COHORT_BUCKETS")

    def test_corrupt_epoch_numbers_never_crash_or_score_green(self):
        base={sec:(500,499) for sec in range(10,36)}
        good=worker(12_000_000,38_000_000,base)
        for key,bad in (
                ("start_us",float("nan")),
                ("start_us",float("inf")),
                ("start_us",float("-inf")),
                ("start_us",float(2**53)),
                ("start_us",False),
                ("sent_entries",float("nan")),
                ("sent_entries",float("inf")),
                ("sent_entries",float("-inf")),
                ("sent_entries",float(2**53)),
                ("received_entries",float("nan")),
                ("received_entries",float("inf")),
                ("received_entries",float("-inf")),
                ("received_entries",float(2**53)),
                ("received_entries",True)):
            with self.subTest(field=key,bad=repr(bad)):
                broken=worker(12_000_000,38_000_000,base)
                broken["cohort_epoch_entries"][7][key]=bad
                self.assertEqual(
                    inspect([good,broken])["cohort_quality"],
                    "INVALID_GLOBAL_COHORT_BUCKETS")
        for key,bad in (("cohort_ready_us",float("nan")),
                        ("cohort_ready_us",float("inf")),
                        ("cohort_ready_us",float("-inf")),
                        ("cohort_ready_us",float(2**53)),
                        ("cohort_finish_us",float("nan")),
                        ("cohort_finish_us",float("inf")),
                        ("cohort_finish_us",float("-inf")),
                        ("cohort_finish_us",float(2**53))):
            with self.subTest(timestamp=key,bad=repr(bad)):
                broken=worker(12_000_000,38_000_000,base)
                broken[key]=bad
                self.assertEqual(
                    inspect([good,broken])["cohort_quality"],
                    "NO_GLOBAL_200_PLAYER_FIVE_SEAT_COHORT")

    def test_malformed_duplicate_epoch_and_bad_received_counts(self):
        data={s:(500,499) for s in range(10,36)}
        a=worker(12_000_000,38_000_000,data)
        b=worker(12_000_000,38_000_000,data)
        b["cohort_epoch_entries"].append(dict(b["cohort_epoch_entries"][0]))
        self.assertEqual(inspect([a,b])["cohort_quality"],"INVALID_GLOBAL_COHORT_BUCKETS")
        b["cohort_epoch_entries"].pop()
        b["cohort_epoch_entries"][0]["start_us"]=14_000_001
        self.assertEqual(inspect([a,b])["cohort_quality"],"INVALID_GLOBAL_COHORT_BUCKETS")
        b["cohort_epoch_entries"][0]["start_us"]=10_000_000
        b["cohort_epoch_entries"][5]["received_entries"]=-3
        self.assertEqual(inspect([a,b])["cohort_quality"],"INVALID_GLOBAL_COHORT_BUCKETS")
        b["cohort_epoch_entries"][5]["received_entries"]=499
        for e in b["cohort_epoch_entries"]:
            e["received_entries"]=e["sent_entries"]+1000
        self.assertEqual(inspect([a,b])["cohort_quality"],
                         "INSUFFICIENT_OR_INVALID_GLOBAL_GAME_COHORT")

if __name__=="__main__":
    unittest.main()
