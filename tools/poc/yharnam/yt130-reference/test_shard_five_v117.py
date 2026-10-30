"""Real-original source guards and fail-closed 200-player five-seat shard QoS."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).parent

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

patch=load("yt117_patch","stage_shard_generator_v117.py")
run=load("yt117_run","run_five_hunter_shards_v117.py")

def sample(shards=3):
    return dict(
        players=200, shards=shards, playing=200, game_receivers=200,
        complete_teams=40, linking=0, lobby=0, awaiting_welcome=0,
        udp_write_failed=0, udp_write_short=0,
        team_name_absent=0, team_name_ambiguous=0,
        team_lookup_throttled=0, team_other_notice=0, team_total_notices=0,
        udp_read_failed=0, udp_read_short=0,
        game_data_datagrams_received=9000, game_data_decode_failed=0,
        game_frame_decode_failed=0, game_frame_bad_header=0,
        game_frame_short_entries=0, game_frame_decoded=9000,
        team_no_invite=0, team_no_code=0, team_full=0,
        team_already_joined=0, team_create_first=0,
        team_world_unavailable=0, team_unknown_other=0,
        game_wire_in_packets=shards*1000,
        game_wire_out_packets=shards*3000,
        game_wire_in_bytes=shards*64000,
        game_wire_out_bytes=shards*192000,
        game_wire_sample_windows=shards*5,
        steady_packets_sent=15000,
        steady_packets_received=15000, steady_workers=4,
        steady_window_ms_min=15000,
        packets_sent=16000, packets_received=16000, packets_lost=0,
        refused=0, udp_buffer_drops=0, relay_ms_p99=11.5,
        redirects=50 if shards==3 else 0, redirect_ms_p99=450 if shards==3 else 0,
        per_shard=[dict(shard=f"lt-{i}", link_thread_cpu_avg=12.5,
                        players_at_end=200//shards, game_wire_in_packets=1000,
                        game_wire_out_packets=3000, game_wire_in_bytes=64000,
                        game_wire_out_bytes=192000, game_wire_sample_windows=5)
                   for i in range(shards)]
    )

class OriginalShardSourceTests(unittest.TestCase):
    def original_source(self):
        return (patch.IMPORT_OLD + "\n" + patch.SPLIT_OLD + "\n" +
                patch.COUNTERS_OLD)
    def test_real_exact_original_shard_script_aggregation(self):
        s = patch.patch_source(self.original_source())
        self.assertIn("import shlex", s)
        self.assertIn("shlex.split(args.extra)", s)
        self.assertIn('sum(r["game_receivers"] for r in results)',s)
        self.assertIn('sum(r["complete_teams"] for r in results)',s)
        self.assertIn('sum(r["steady_packets_sent"] for r in results)',s)
        self.assertIn('sum(r["steady_packets_received"] for r in results)',s)
        self.assertIn('min(r["steady_window_ms"] for r in results)',s)
        self.assertIn('sum(r["packets_sent"] for r in results)',s)
        for key in ("udp_write_failed", "udp_write_short", "linking", "lobby",
                    "awaiting_welcome"):
            self.assertIn(f'sum(r["{key}"] for r in results)',s)
        self.assertIn('sum(r["packets_received"] for r in results)',s)
        self.assertEqual(patch.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(patch.BLOB, "9a8e6a1dd866f9ef996ed544e3b781953e154230")
    def test_fails_closed_when_original_source_is_unknown(self):
        s=self.original_source()
        with self.assertRaisesRegex(ValueError,"twice"):
            patch.patch_source(patch.patch_source(s))
        for anchor in (patch.IMPORT_OLD,patch.SPLIT_OLD,patch.COUNTERS_OLD):
            with self.subTest(anchor=anchor[:20]):
                with self.assertRaises(ValueError):
                    patch.patch_source(s.replace(anchor,"BROKEN"))

class OriginalShardsQoSTests(unittest.TestCase):
    def test_actual_five_player_shards_must_pass_all_quality_gates(self):
        for shards in (1,3):
            with self.subTest(shards=shards):
                self.assertEqual(run.grade(sample(shards),shards)["quality"],
                                 "FULL_GAMEPLAY_SYNTHETIC_ONLY")
                s=sample(shards)
                s["relay_ms_p99"]=151
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "RELAY_P99_OVER_50MS")
                s=sample(shards)
                s["game_receivers"]=199
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "GAME_RECEIVERS_MISSING")
                s=sample(shards)
                s["complete_teams"]=39
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "FIVE_HUNTER_TEAMS_INCOMPLETE")
                s=sample(shards)
                s["packets_received"]=14000
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "REAL_GAME_DELIVERY_DEGRADED")
                s=sample(shards)
                s["steady_packets_received"]=10000
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "STEADY_DELIVERY_DEGRADED")
                s=sample(shards)
                s["steady_workers"]=3
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "NO_FIVE_HUNTER_STEADY_WINDOW")
                s=sample(shards)
                s["steady_window_ms_min"]=4999
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "NO_FIVE_HUNTER_STEADY_WINDOW")
                s=sample(shards)
                s["udp_buffer_drops"]=1
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "HOST_KERNEL_UDP_DROPS")
                s=sample(shards)
                s["playing"]=199
                s["lobby"]=1
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "NOT_ALL_PLAYING")
                s=sample(shards)
                s["udp_write_failed"]=1
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "GENERATOR_UDP_SOCKET_WRITE_FAILED")
                s=sample(shards)
                s["udp_write_short"]=1
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "GENERATOR_UDP_SOCKET_WRITE_FAILED")
                s=sample(shards)
                s["per_shard"][0]["link_thread_cpu_avg"]=90
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "SHARD_CPU_SATURATED")
    def test_socket_diagnostics_and_200_original_player_states_sum_correctly(self):
        s=sample(3)
        s["playing"]=190
        s["lobby"]=7
        s["awaiting_welcome"]=3
        report=run.grade(s,3)
        self.assertEqual(report["quality"],"NOT_ALL_PLAYING")
        self.assertEqual((report["linking"], report["lobby"],
                          report["awaiting_welcome"]), (0,7,3))
        s["linking"]=1
        self.assertEqual(run.grade(s,3)["quality"],
                         "INVALID_ORIGINAL_GAME_LIFECYCLE_SUM")
        s=sample(3)
        s["udp_write_failed"]=2
        report=run.grade(s,3)
        self.assertEqual(report["quality"],"GENERATOR_UDP_SOCKET_WRITE_FAILED")
        self.assertEqual(report["udp_write_failed"],2)

    def test_startup_losses_are_never_mislabeled_as_healthy_200(self):
        report=sample(3)
        report["packets_received"]=14500
        result=run.grade(report,3)
        self.assertEqual(result["quality"],"REAL_GAME_DELIVERY_DEGRADED")
        self.assertEqual(result["steady_quality"],
                         "STEADY_DELIVERY_PASS_SYNTHETIC_ONLY")
        self.assertEqual(result["steady_delivered_pct"],100.0)

    def test_cross_shard_redirects_must_really_happen(self):
        s=sample(3)
        s["redirects"]=0
        self.assertEqual(run.grade(s,3)["quality"],"CROSS_SHARD_REDIRECT_FAILED")
        s=sample(3)
        s["redirect_ms_p99"]=3000
        self.assertEqual(run.grade(s,3)["quality"],"CROSS_SHARD_REDIRECT_FAILED")
    def test_v158_v159_original_receive_counters_reconciled_in_durable_json(self):
        for shards in (1,3):
            data=sample(shards)
            result=run.grade(data,shards)
            self.assertEqual(result["quality"],"FULL_GAMEPLAY_SYNTHETIC_ONLY")
            self.assertEqual(result["game_frame_decoded"],9000)
            self.assertEqual(result["game_data_datagrams_received"],9000)
            data["team_other_notice"]=5
            data["team_no_invite"]=2
            data["team_already_joined"]=3
            result=run.grade(data,shards)
            self.assertEqual(result["team_no_invite"],2)
            self.assertEqual(result["team_already_joined"],3)
            self.assertEqual(result["team_other_notice"],5)
            for field in ("udp_read_failed","udp_read_short",
                          "game_data_datagrams_received","game_data_decode_failed",
                          "game_frame_decode_failed","game_frame_bad_header",
                          "game_frame_short_entries","game_frame_decoded",
                          "team_no_invite","team_no_code","team_full",
                          "team_already_joined","team_create_first",
                          "team_world_unavailable","team_unknown_other"):
                with self.subTest(shards=shards,field=field):
                    broken=dict(data)
                    broken.pop(field)
                    self.assertEqual(run.grade(broken,shards)["quality"],
                                     "MISSING_OR_INVALID_QT_CLIENT_RECEIVE_OR_JOIN_DETAILS")
            data["game_data_datagrams_received"]+=1
            self.assertEqual(run.grade(data,shards)["quality"],
                             "QT_CLIENT_GAME_DATA_FRAME_COUNTER_MISMATCH")
            data["game_data_datagrams_received"]-=1
            data["team_unknown_other"]+=1
            self.assertEqual(run.grade(data,shards)["quality"],
                             "ORIGINAL_LOBBY_OTHER_NOTICE_DETAIL_MISMATCH")
            data["team_unknown_other"]-=1
            data["udp_read_failed"]=1
            self.assertEqual(run.grade(data,shards)["quality"],
                             "GENERATOR_UDP_SOCKET_READ_FAILED")
            data["udp_read_failed"]=0
            data["game_frame_bad_header"]=1
            data["game_frame_decoded"]-=1
            self.assertEqual(run.grade(data,shards)["quality"],
                             "GENERATOR_GAME_DATA_DECODE_REJECTED")

    def test_v157_fixed_population_multiple_real_generator_processes(self):
        from argparse import Namespace
        for workers in (4, 8, 16):
            for shards in (1, 3):
                with self.subTest(workers=workers,shards=shards):
                    args=Namespace(shadnet=Path("/unused/source-verified/shadnet"),
                                   bbload=Path("/unused/source-verified/bbload"),
                                   shard_script=Path("/unused/source-verified/run_shards.py"),
                                   cross="mixed",owners=5,load_processes=workers)
                    cmd=run.command(args,shards,39014)
                    self.assertEqual(cmd[cmd.index("--players")+1],"200")
                    self.assertEqual(cmd[cmd.index("--team-size")+1],"5")
                    self.assertEqual(cmd[cmd.index("--processes")+1],str(workers))
                    self.assertEqual(cmd[cmd.index("--seconds")+1],str(run.RUN_SECONDS))
                    good=sample(shards)
                    good["steady_workers"]=workers
                    self.assertEqual(run.grade(good,shards,workers)["quality"],
                                     "FULL_GAMEPLAY_SYNTHETIC_ONLY")
                    for wrong in (4,8,16):
                        if wrong!=workers:
                            self.assertEqual(
                                run.grade(good,shards,wrong)["quality"],
                                "NO_FIVE_HUNTER_STEADY_WINDOW")
                    poor=sample(shards)
                    poor["steady_workers"]=workers
                    poor["steady_packets_received"]=10000
                    self.assertEqual(run.grade(poor,shards,workers)["quality"],
                                     "STEADY_DELIVERY_DEGRADED")
                    poor["packets_lost"]=10
                    self.assertEqual(run.grade(poor,shards,workers)["quality"],
                                     "REAL_GAME_DELIVERY_DEGRADED")
        with self.assertRaises(ValueError):
            run.grade(sample(1),1,5)

    def test_v156_original_lobby_refusal_category_consistency(self):
        for shards in (1,3):
            data=sample(shards)
            self.assertEqual(run.grade(data,shards)["quality"],
                             "FULL_GAMEPLAY_SYNTHETIC_ONLY")
            data.update(team_name_absent=11, team_name_ambiguous=2,
                        team_lookup_throttled=3, team_other_notice=5,
                        team_total_notices=21)
            out=run.grade(data,shards)
            self.assertEqual(out["quality"],"FULL_GAMEPLAY_SYNTHETIC_ONLY")
            self.assertEqual(out["team_name_absent"],11)
            self.assertEqual(out["team_lookup_throttled"],3)
            self.assertIn("not unique players",out["notice_scope"])
            for key in ("team_name_absent","team_name_ambiguous",
                        "team_lookup_throttled","team_other_notice",
                        "team_total_notices"):
                with self.subTest(shards=shards,field=key):
                    bad=dict(data)
                    bad[key]=-1
                    self.assertEqual(run.grade(bad,shards)["quality"],
                                     "MISSING_REAL_LOBBY_REFUSAL_COUNTS")
                    bad=dict(data)
                    bad[key]=True
                    self.assertEqual(run.grade(bad,shards)["quality"],
                                     "MISSING_REAL_LOBBY_REFUSAL_COUNTS")
                    bad=dict(data)
                    bad[key]+=1
                    self.assertEqual(run.grade(bad,shards)["quality"],
                                     "INCONSISTENT_REAL_LOBBY_REFUSAL_COUNTS")
            bad=dict(data)
            bad["packets_received"]=max(0,bad["packets_sent"]-10000)
            self.assertEqual(run.grade(bad,shards)["quality"],
                             "REAL_GAME_DELIVERY_DEGRADED")

    def test_v155_original_qt_wire_aggregate_verification(self):
        for shards in (1, 3):
            item=sample(shards)
            report=run.grade(item, shards)
            self.assertEqual(report["quality"], "FULL_GAMEPLAY_SYNTHETIC_ONLY")
            self.assertEqual(report["game_wire_in_packets"], shards*1000)
            self.assertEqual(report["game_wire_out_packets"], shards*3000)
            self.assertEqual(report["game_wire_sample_windows"], shards*5)
            self.assertIn("whole run", report["wire_scope"])
            for field in ("game_wire_in_packets","game_wire_out_packets",
                          "game_wire_in_bytes","game_wire_out_bytes",
                          "game_wire_sample_windows"):
                with self.subTest(shards=shards, field=field):
                    broken=sample(shards)
                    broken.pop(field)
                    self.assertEqual(run.grade(broken,shards)["quality"],
                                     "MISSING_REAL_QT_WIRE_COUNTERS")
                    broken=sample(shards)
                    broken[field]+=1
                    self.assertEqual(run.grade(broken,shards)["quality"],
                                     "QT_WIRE_COUNTER_TOTAL_MISMATCH")
                    broken=sample(shards)
                    broken["per_shard"][0][field]=None
                    self.assertEqual(run.grade(broken,shards)["quality"],
                                     "INVALID_QT_SHARD_WIRE_COUNTERS")
            no_sample=sample(shards)
            no_sample["game_wire_sample_windows"]-=5
            no_sample["per_shard"][0]["game_wire_sample_windows"]=0
            self.assertEqual(run.grade(no_sample,shards)["quality"],
                             "QT_GAME_DATA_WIRE_SAMPLES_MISSING")
            actual_loss=sample(shards)
            actual_loss["steady_packets_received"]=10000
            self.assertEqual(run.grade(actual_loss,shards)["quality"],
                             "STEADY_DELIVERY_DEGRADED")
            actual_loss["per_shard"][0]["game_wire_sample_windows"]=0
            actual_loss["game_wire_sample_windows"]-=5
            # Existing strict QoS verdict must never be hidden by diagnostics.
            self.assertEqual(run.grade(actual_loss,shards)["quality"],
                             "STEADY_DELIVERY_DEGRADED")

    def test_unknown_bad_or_fake_values_must_fail_closed(self):
        for key,value in [
            ("shards",1),("players",199),("playing","200"),("game_receivers",None),
            ("packets_lost",-1),("packets_sent",float("nan")),
            ("linking",-1),("lobby","0"),("awaiting_welcome",None),
            ("udp_write_failed",-1),("udp_write_short",float("nan")),
            ("complete_teams",None),("complete_teams",False),
            ("steady_packets_sent",None),("steady_workers",True),
            ("steady_window_ms_min",float("nan")),
            ("relay_ms_p99",float("inf")),("udp_buffer_drops",True),
            ("per_shard",[]),("per_shard",[{},{}]),
            ("per_shard",[{"shard":["unsafe"]}, {}, {}]),
            ("per_shard", [{"shard":"lt-0","link_thread_cpu_avg":"0"},
                           {"shard":"lt-1","link_thread_cpu_avg":5},
                           {"shard":"lt-2","link_thread_cpu_avg":5}]),
        ]:
            s=sample(3)
            s[key]=value
            with self.subTest(key=key,value=str(value)[:20]):
                self.assertNotEqual(run.grade(s,3).get("quality"),
                                    "FULL_GAMEPLAY_SYNTHETIC_ONLY")
    def test_five_hunter_enemy_owner_cases_use_verified_original_cli(self):
        # Upstream YT #444 support already exists in the source-exact
        # stage_five_player_bbload.py. Never pretend default --owners 1
        # describes five hunters spread across the map.
        from types import SimpleNamespace
        args=SimpleNamespace(shadnet=Path("/tmp/shadnet"),
                             bbload=Path("/tmp/bbload"),
                             shard_script=Path("/tmp/run_shards.py"),
                             owners=5)
        for count in run.OWNER_CASES:
            with self.subTest(owners=count):
                args.owners=count
                cmd=run.command(args,3,39014)
                self.assertEqual(cmd[cmd.index("--team-size")+1],"5")
                self.assertEqual(cmd[cmd.index("--players")+1],"200")
                self.assertIn(f"--owners {count}",cmd[cmd.index("--extra")+1])
                self.assertIn("--owner-fps 30",cmd[cmd.index("--extra")+1])
        self.assertEqual(run.OWNER_CASES,(1,3,5))
        self.assertEqual(run.CROSS_MODES,("mixed","code","invite"))
        for mode in run.CROSS_MODES:
            args.cross=mode
            cmd=run.command(args,3,39014)
            self.assertEqual(cmd[cmd.index("--cross")+1],mode)

    def test_five_seat_real_200_by_shard_not_two_or_four(self):
        self.assertEqual(run.SIZE,5)
        self.assertEqual(run.POPULATION,200)
        self.assertEqual(run.SHARD_COUNTS,(1,3))
        self.assertEqual(run.TIMEOUT,120)

if __name__=="__main__":
    unittest.main()
