"""Fail-closed scale matrix and reporter checks; no processes or live sockets."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location("yt_scale_test", BASE / "run_scale_1000.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Scale1000PlanTests(unittest.TestCase):
    def test_real_1000_and_optional_2000_targets_are_explicit(self):
        self.assertEqual(m.stages(2, 1000), (250, 500, 1000))
        self.assertEqual(m.stages(4, 1024), (256, 512, 1024))
        self.assertEqual(m.stages(2, 2000), (250, 500, 1000, 2000))
        self.assertEqual(m.stages(4, 2048), (256, 512, 1024, 2048))
        for team, peak in ((2, 1024), (4, 1000), (4, 400), (2, 10000)):
            with self.assertRaises(ValueError):
                m.stages(team, peak)

    def test_full_and_reduced_gameplay_have_actual_fps(self):
        class Args:
            load_script = Path("/tmp/yt/run_load.py")
            shadnet = Path("/tmp/yt/shadnet")
            bbload = Path("/tmp/yt/bbload")
            team_size = 2
            profile = "active"
            ramp_ms = 20
        command = m.make_command(Args(), 1000, 2)
        self.assertEqual(command[command.index("--players") + 1], "1000")
        self.assertEqual(command[command.index("--team-size") + 1], "2")
        self.assertEqual(command[command.index("--processes") + 1], "10")
        self.assertIn("--owner-fps 30 --follower-fps 8", command[-1])
        self.assertEqual(command[command.index("--ramp-ms")+1], "20")
        self.assertIn("CheckServerBuild=false", command)
        self.assertEqual(m.processes(2048), 21)
        Args.profile = "reduced"
        self.assertIn("--owner-fps 10 --follower-fps 3",
                      m.make_command(Args(), 1000, 2)[-1])
        Args.profile = "presence"
        self.assertIn("--owner-fps 1 --follower-fps 1",
                      m.make_command(Args(), 1000, 2)[-1])

    @staticmethod
    def playing(players=1000, p99=21.0, received=300000):
        return {
            "players": players, "playing": players,
            "packets_sent": 300000, "packets_received": received,
            "packets_lost": max(0, 300000 - received),
            "relay_ms_p99": p99, "main_thread_cpu_avg": 14.0,
            "server_rss_mb_max": 100, "server_threads": 5,
        }

    def test_1000_online_is_not_1000_healthy_gameplay(self):
        full = m.inspect(json.dumps(self.playing()) + "\n", 0, 1000)
        self.assertEqual(full["quality"], "FULL_GAMEPLAY")
        self.assertTrue(full["observed"])
        partial = self.playing()
        partial["playing"] = 600
        self.assertEqual(
            m.inspect(json.dumps(partial), 0, 1000)["quality"], "PARTIAL_GAMEPLAY")
        self.assertEqual(
            m.inspect(json.dumps(self.playing(received=260000)), 0, 1000)["quality"],
            "DELIVERY_DEGRADED")
        self.assertEqual(
            m.inspect(json.dumps(self.playing(p99=225)), 0, 1000)["quality"],
            "RELAY_LATENCY_DEGRADED")

    def test_private_temp_server_diagnostics_are_only_aggregate(self):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="yt130-test-") as tmp:
            root = Path(tmp)
            sub = root / "shadnet-load-fixture"
            sub.mkdir()
            (sub / "shadnet.log").write_text(
                "INFO YT130_EVENTLOOP read_batches=1 read_datagrams=8"
                " read_busy_us=220 max_read_batch_us=220"
                " max_read_batch_datagrams=8 world_ticks=1"
                " world_busy_us=100 max_world_busy_us=100"
                " max_world_gap_us=81000 late_world_ticks=1\n"
                "YT130_UDP_FAIR_QUEUE slices=3 handled=8 max_slice_us=1300"
                " max_queued=12 overload_drops=3 queued=1\n"
                "refused player_secret abc123 at 192.0.2.55\n"
                "hello player_secret abc123\n"
            )
            report = m.inspect_disposable_server_logs(root)
            self.assertEqual(report["logs_found"], 1)
            self.assertEqual(report["eventloop"]["metrics"]["late_world_ticks"], 1)
            self.assertEqual(report["fair_queue"]["metrics"]["overload_drops"], 3)
            self.assertEqual(report["server_log_events"]["refused"], 1)
            self.assertNotIn("abc123", json.dumps(report))
            self.assertNotIn("192.0.2.55", json.dumps(report))

    def test_missing_temporary_source_never_fakes_diagnostics(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            report = m.inspect_disposable_server_logs(Path(tmp))
            self.assertEqual(report["logs_found"], 0)
            self.assertEqual(report["folder_count_mismatch"], 0)

    def test_no_green_when_generator_times_out_or_fakes_numbers(self):
        self.assertEqual(m.inspect("", 124, 1000)["quality"], "TIMEOUT")
        self.assertEqual(m.inspect("", 1, 1000)["quality"], "GENERATOR_FAILED")
        self.assertEqual(m.inspect("{not json}", 0, 1000)["quality"], "GENERATOR_FAILED")
        self.assertEqual(m.inspect(json.dumps(self.playing(500)), 0, 1000)
                         ["quality"], "GENERATOR_MISMATCH")
        rows = json.dumps(self.playing()) + "\n" + json.dumps(self.playing())
        self.assertEqual(m.inspect(rows, 0, 1000)["quality"], "GENERATOR_FAILED")
        with self.assertRaises(ValueError):
            m.measure(["/bin/true"], 5000)

    def test_process_group_killed_instead_of_orphaning_server(self):
        class Fake:
            pid = 12345
            returncode = -9
            count = 0
            def communicate(self, timeout=None):
                self.count += 1
                if timeout is not None:
                    import subprocess
                    raise subprocess.TimeoutExpired(cmd=["fake"], timeout=timeout)
                return "partial", "cleanup"
        with patch.object(m.subprocess, "Popen", return_value=Fake()) as pop:
            with patch.object(m.os, "killpg") as kill:
                rc, out, err = m.measure(["/fake/local/run_load.py"], 90)
        self.assertEqual((rc, out), (124, ""))
        self.assertIn("PROCESS_GROUP_KILLED", err)
        self.assertTrue(pop.call_args.kwargs["start_new_session"])
        kill.assert_called_once_with(12345, m.signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
