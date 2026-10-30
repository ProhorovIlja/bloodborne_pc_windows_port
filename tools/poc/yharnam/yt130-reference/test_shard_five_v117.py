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
        complete_teams=40, steady_packets_sent=15000,
        steady_packets_received=15000, steady_workers=4,
        steady_window_ms_min=15000,
        packets_sent=16000, packets_received=16000, packets_lost=0,
        refused=0, udp_buffer_drops=0, relay_ms_p99=11.5,
        redirects=50 if shards==3 else 0, redirect_ms_p99=450 if shards==3 else 0,
        per_shard=[dict(shard=f"lt-{i}", link_thread_cpu_avg=12.5,
                        players_at_end=200//shards) for i in range(shards)]
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
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "NOT_ALL_PLAYING")
                s=sample(shards)
                s["per_shard"][0]["link_thread_cpu_avg"]=90
                self.assertEqual(run.grade(s,shards)["quality"],
                                 "SHARD_CPU_SATURATED")
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
    def test_unknown_bad_or_fake_values_must_fail_closed(self):
        for key,value in [
            ("shards",1),("players",199),("playing","200"),("game_receivers",None),
            ("packets_lost",-1),("packets_sent",float("nan")),
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
