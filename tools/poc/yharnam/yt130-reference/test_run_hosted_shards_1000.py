"""Offline guardrails for original YT1.3 Hosted=true sharded scale 1000/2000."""
import importlib.util
from pathlib import Path
import sys
import json
import tempfile
import subprocess
import unittest
from unittest.mock import patch

FOLDER = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "yt_hosted_shards_measure", FOLDER / "run_hosted_shards_1000.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HostedShards1000Tests(unittest.TestCase):
    @staticmethod
    def args():
        class A:
            load_script = Path("/original/server/loadtest/run_shards.py")
            shadnet = Path("/original/build/shadnet")
            bbload = Path("/original/build/bbload")
            team_size = 2
            profile = "active"
            seconds = 24
            ramp_ms = 30
        return A()

    def test_1000_and_2000_have_exact_population_and_shard_comparison(self):
        self.assertEqual(m.stages(2, 1000), (250, 500, 1000))
        self.assertEqual(m.stages(2, 2000), (250, 500, 1000, 2000))
        self.assertEqual(m.stages(4, 1024), (256, 512, 1024))
        self.assertEqual(m.stages(4, 2048), (256, 512, 1024, 2048))
        for team, peak in ((2, 1024), (4, 1000), (2, 7), (4, 2000)):
            with self.subTest(team=team, peak=peak), self.assertRaises(ValueError):
                m.stages(team, peak)

    def test_uses_original_hosted_shards_test_and_actual_game_frame_fps(self):
        args = self.args()
        cmd = m.build_command(args, 3, 1000, 2)
        self.assertIn("--shards", cmd)
        self.assertEqual(cmd[cmd.index("--shards")+1], "3")
        self.assertEqual(cmd[cmd.index("--players")+1], "1000")
        self.assertEqual(cmd[cmd.index("--capacity")+1], "800")
        self.assertEqual(cmd[cmd.index("--cross")+1], "mixed")
        self.assertEqual(cmd[-1], "--build '" + m.BUILD + "' --owner-fps 30 --follower-fps 8")
        import shlex
        self.assertEqual(shlex.split(cmd[-1])[1], m.BUILD)
        args.profile = "reduced"
        self.assertEqual(m.build_command(args, 1, 250, 0)[-1],
                         "--build '" + m.BUILD + "' --owner-fps 10 --follower-fps 3")
        with self.assertRaises(ValueError):
            m.build_command(args, 5, 1000, 3)

    @staticmethod
    def sample(players=1000, shards=3, p99=9, received=40000, lost=0, playing=None):
        if playing is None:
            playing = players
        return {
            "players": players, "shards": shards,
            "playing": playing, "relay_ms_p99": p99,
            "redirects": 0 if shards == 1 else 100,
            "redirect_ms_p99": 0 if shards == 1 else 120,
            "packets_received": received, "packets_lost": lost,
            "udp_buffer_drops": 0,
            "per_shard": [
                {"shard": f"lt-{i}", "players_at_end": int(players/shards),
                 "link_thread_cpu_avg": 19, "link_thread_cpu_max": 70}
                for i in range(shards)
            ],
        }

    def test_1000_connected_never_equates_to_1000_playing(self):
        line = json.dumps(self.sample())
        self.assertEqual(m.report(line, 0, 1000, 3)["quality"], "FULL_GAMEPLAY")
        self.assertEqual(m.report(json.dumps(self.sample(playing=999)), 0, 1000, 3)
                         ["quality"], "PARTIAL_PLAYING")
        self.assertEqual(m.report(json.dumps(self.sample(received=3)), 0, 1000, 3)
                         ["quality"], "INSUFFICIENT_GAME_FRAMES")
        self.assertEqual(m.report(json.dumps(self.sample(lost=900)), 0, 1000, 3)
                         ["quality"], "GAME_PACKET_LOSS")
        self.assertEqual(m.report(json.dumps(self.sample(p99=200)), 0, 1000, 3)
                         ["quality"], "RELAY_P99_OVER_50MS")
        highcpu = self.sample()
        highcpu["per_shard"][0]["link_thread_cpu_avg"] = 92
        self.assertEqual(m.report(json.dumps(highcpu), 0, 1000, 3)
                         ["quality"], "SHARD_MAIN_CPU_SATURATED")
        not_crossed = self.sample()
        not_crossed["redirects"] = 0
        self.assertEqual(m.report(json.dumps(not_crossed), 0, 1000, 3)
                         ["quality"], "CROSS_SHARD_NOT_EXERCISED")
        too_slow_join = self.sample()
        too_slow_join["redirect_ms_p99"] = 23000
        self.assertEqual(m.report(json.dumps(too_slow_join), 0, 1000, 3)
                         ["quality"], "CROSS_SHARD_JOIN_TOO_SLOW")

    def test_missing_invalid_artifact_fails_closed(self):
        self.assertEqual(m.report("", 124, 250, 1)["quality"], "TIMEOUT")
        self.assertEqual(m.report("", 1, 250, 1)["quality"], "ORIGINAL_GENERATOR_FAILED")
        self.assertEqual(m.report("garbage", 0, 250, 1)
                         ["quality"], "MISSING_OR_DUPLICATE_JSON")
        src = self.sample()
        self.assertEqual(m.report(json.dumps(src), 0, 500, 3)
                         ["quality"], "WRONG_POPULATION_OR_SHARDS")
        src["per_shard"] = []
        self.assertEqual(m.report(json.dumps(src), 0, 1000, 3)
                         ["quality"], "NO_PER_SHARD_EVIDENCE")
        src = self.sample()
        dup = json.dumps(src) + "\n" + json.dumps(src)
        self.assertEqual(m.report(dup, 0, 1000, 3)["quality"],
                         "MISSING_OR_DUPLICATE_JSON")

    def test_nonfinite_or_fabricated_shard_json_never_green(self):
        cases = [
            ("relay_ms_p99", float("nan"), "INVALID_COUNTERS"),
            ("relay_ms_p99", float("inf"), "INVALID_COUNTERS"),
            ("packets_received", True, "INVALID_COUNTERS"),
            ("redirects", float("nan"), "INVALID_CROSS_SHARD_COUNTERS"),
            ("redirect_ms_p99", float("inf"), "INVALID_CROSS_SHARD_COUNTERS"),
        ]
        for key, invalid, expected in cases:
            with self.subTest(key=key, invalid=invalid):
                source = self.sample()
                source[key] = invalid
                self.assertEqual(
                    m.report(json.dumps(source), 0, 1000, 3)["quality"], expected)
        source = self.sample()
        source["per_shard"][0]["link_thread_cpu_avg"] = float("nan")
        self.assertEqual(m.report(json.dumps(source), 0, 1000, 3)
                         ["quality"], "INVALID_PER_SHARD_CPU")
        source = self.sample()
        source["per_shard"][1]["shard"] = source["per_shard"][0]["shard"]
        self.assertEqual(m.report(json.dumps(source), 0, 1000, 3)
                         ["quality"], "NO_PER_SHARD_EVIDENCE")
        # Broken or malicious JSON must not terminate the whole 1000-player
        # benchmark while trying to hash an untrusted shard identifier.
        for bad_id in ([], {}, None, 0, "", "x" * 129, float("nan")):
            with self.subTest(shard_id=bad_id):
                source = self.sample()
                source["per_shard"][0]["shard"] = bad_id
                self.assertEqual(m.report(json.dumps(source), 0, 1000, 3)
                                 ["quality"], "NO_PER_SHARD_EVIDENCE")
        source = self.sample()
        del source["per_shard"][0]["shard"]
        self.assertEqual(m.report(json.dumps(source), 0, 1000, 3)
                         ["quality"], "NO_PER_SHARD_EVIDENCE")

    def test_timeout_kills_all_original_server_directory_redis_descendants(self):
        class Fake:
            pid = 888
            returncode = -9
            def communicate(self, timeout=None):
                if timeout is not None:
                    raise subprocess.TimeoutExpired(["run_shards.py"], timeout)
                return "", ""
        with patch.object(m.subprocess, "Popen", return_value=Fake()) as pop:
            with patch.object(m.os, "killpg") as kill:
                self.assertEqual(m.execute(["python", "run_shards.py"], 90), (124, ""))
        self.assertTrue(pop.call_args.kwargs["start_new_session"])
        kill.assert_called_once_with(888, m.signal.SIGKILL)

    def test_real_safety_limiter_and_original_pin(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.SHARD_COUNTS, (1, 3))
        self.assertEqual(m.MAX_TIMEOUT, 240)
        with self.assertRaises(ValueError):
            m.execute(["python", "run_shards.py"], 900)


if __name__ == "__main__":
    unittest.main()
