"""Fail-closed scale matrix and reporter checks; no processes or live sockets."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
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
        self.assertEqual(m.stages(5, 1000), (250, 500, 1000))
        self.assertEqual(m.stages(5, 2000), (250, 500, 1000, 2000))
        self.assertEqual(m.stages(5, 250), (250,))
        for team, peak in ((2, 1024), (4, 1000), (4, 400), (2, 10000),
                           (5, 1024), (5, 2048), (1, 250)):
            with self.assertRaises(ValueError):
                m.stages(team, peak)

    def test_full_and_reduced_gameplay_have_actual_fps(self):
        class Args:
            load_script = Path("/tmp/yt/run_load.py")
            shadnet = Path("/tmp/yt/shadnet")
            bbload = Path("/tmp/yt/bbload")
            team_size = 2
            profile = "active"
        command = m.make_command(Args(), 1000, 2)
        self.assertEqual(command[command.index("--players") + 1], "1000")
        self.assertEqual(command[command.index("--team-size") + 1], "2")
        self.assertEqual(command[command.index("--processes") + 1], "10")
        self.assertIn("--owner-fps 30 --follower-fps 8", command[-1])
        self.assertIn("CheckServerBuild=false", command)
        self.assertEqual(m.processes(2048), 21)
        Args.team_size = 5
        self.assertEqual(m.make_command(Args(), 1000, 2)[
            m.make_command(Args(), 1000, 2).index("--team-size") + 1], "5")
        Args.profile = "reduced"
        self.assertIn("--owner-fps 10 --follower-fps 3",
                      m.make_command(Args(), 1000, 2)[-1])
        Args.profile = "presence"
        self.assertIn("--owner-fps 1 --follower-fps 1",
                      m.make_command(Args(), 1000, 2)[-1])

    def test_real_upstream_multi_owner_packets_are_bounded_and_marked(self):
        class Args:
            load_script = Path("/tmp/yt/run_load.py")
            shadnet = Path("/tmp/yt/shadnet")
            bbload = Path("/tmp/yt/bbload")
            team_size = 5
            profile = "active"
            owners = 4
        opts = Args()
        cmd = m.make_command(opts, 1000, 0)
        self.assertIn("--owners 4", cmd[-1])
        self.assertEqual(m.owners_per_team(opts), 4)
        opts.owners = 5
        self.assertIn("--owners 5", m.make_command(opts, 1000, 0)[-1])
        for invalid in (0, -1, 6, 1.5, "5", None):
            opts.owners = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    m.owners_per_team(opts)
        opts.owners = 4
        opts.team_size = 2
        with self.assertRaises(ValueError):
            m.owners_per_team(opts)
        opts.owners = 1
        self.assertIn("--owners 1", m.make_command(opts, 250, 0)[-1])

    def test_five_hunter_generator_must_never_silently_clamp_to_four(self):
        from subprocess import CompletedProcess
        patched = CompletedProcess(args=["bbload", "--help"], returncode=0,
                                   stdout="players a team (2-5)", stderr="")
        original = CompletedProcess(args=["bbload", "--help"], returncode=0,
                                    stdout="players a team (2-4)", stderr="")
        with patch.object(m.subprocess, "run", return_value=patched):
            m.verify_five_player_generator(Path("/tmp/bbload"))
        with patch.object(m.subprocess, "run", return_value=original):
            with self.assertRaisesRegex(ValueError, "silently clamps"):
                m.verify_five_player_generator(Path("/tmp/bbload"))

    def test_actual_owner_generator_help_is_required_not_assumed(self):
        from subprocess import CompletedProcess
        valid = CompletedProcess(args=["bbload", "--help"], returncode=0,
                                 stdout="--owners <n> enemy-owner seats", stderr="")
        legacy = CompletedProcess(args=["bbload", "--help"], returncode=0,
                                  stdout="players a team (2-5)", stderr="")
        with patch.object(m.subprocess, "run", return_value=valid):
            m.verify_multi_owner_generator(Path("/tmp/bbload"))
        with patch.object(m.subprocess, "run", return_value=legacy):
            with self.assertRaisesRegex(ValueError, "Missing source-pinned"):
                m.verify_multi_owner_generator(Path("/tmp/bbload"))

    @staticmethod
    def playing(players=1000, p99=21.0, received=300000):
        return {
            "players": players, "playing": players,
            "game_receivers": players,
            "packets_sent": 300000, "packets_received": received,
            "packets_lost": max(0, 300000 - received),
            "relay_ms_p99": p99, "main_thread_cpu_avg": 14.0,
            "server_rss_mb_max": 100, "server_threads": 5,
        }

    def test_1000_online_is_not_1000_healthy_gameplay(self):
        full = m.inspect(json.dumps(self.playing()) + "\n", 0, 1000)
        self.assertEqual(full["quality"], "FULL_GAMEPLAY")
        self.assertTrue(full["observed"])
        self.assertEqual(full["metrics"]["packets_lost"], 0)
        self.assertEqual(full["metrics"]["game_receivers"], 1000)
        missing = self.playing()
        missing["game_receivers"] = 999
        self.assertEqual(m.inspect(json.dumps(missing), 0, 1000)["quality"],
                         "GAME_RECIPIENTS_MISSING")
        # This report must not claim healthy gameplay when the native
        # generator observes holes even if fanout inflates receives.
        with_gaps = self.playing(received=400000)
        with_gaps["packets_lost"] = 10000
        degraded = m.inspect(json.dumps(with_gaps), 0, 1000)
        self.assertEqual(degraded["quality"], "SEQUENCE_GAPS_DEGRADED")
        self.assertEqual(degraded["metrics"]["packets_lost"], 10000)
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

    def test_automated_scale_stops_after_first_unhealthy_cohort(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            paths = [base / "shadnet", base / "bbload", base / "run_load.py"]
            for path in paths:
                path.write_text("fixture", encoding="utf-8")
            args = SimpleNamespace(
                shadnet=paths[0], bbload=paths[1], load_script=paths[2],
                output=base / "report.jsonl", team_size=2, profile="active",
                owners=1, peak=1000, timeout=90, require_healthy=True,
                continue_after_unhealthy=False,
            )
            first = json.dumps(self.playing(players=250, p99=125))
            with patch.object(m, "measure", return_value=(0, first, "")) as measured:
                self.assertEqual(m.run(args), 1)
            self.assertEqual(measured.call_count, 1)
            rows = [json.loads(row) for row in args.output.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["quality"], "RELAY_LATENCY_DEGRADED")
            self.assertEqual(rows[0]["stage_players"], 250)
            self.assertEqual(rows[0]["owner_model"], "UPSTREAM_YT_PR444_PINNED_SOURCE")

            # An explicit diagnostic may still inspect 500 and 1000:
            # no fabricated green scores or early positive return.
            args.continue_after_unhealthy = True
            cases = [(0, json.dumps(self.playing(players=p, p99=125)), "")
                     for p in (250, 500, 1000)]
            with patch.object(m, "measure", side_effect=cases) as measured:
                self.assertEqual(m.run(args), 1)
            self.assertEqual(measured.call_count, 3)
            self.assertEqual(len(args.output.read_text().splitlines()), 3)

    def test_timeout_cleanup_survives_already_exited_group(self):
        class Fake:
            pid = 32314
            returncode = -9
            def communicate(self, timeout=None):
                if timeout is not None:
                    from subprocess import TimeoutExpired
                    raise TimeoutExpired(cmd=["synthetic"], timeout=timeout)
                return "partial", "cleaned"
        with patch.object(m.subprocess, "Popen", return_value=Fake()):
            with patch.object(m.os, "killpg", side_effect=ProcessLookupError) as killed:
                self.assertEqual(m.measure(["/local/run_load.py"], 90)[0], 124)
        killed.assert_called_once_with(32314, m.signal.SIGKILL)

    def test_keyboard_interrupt_reaps_entire_synthetic_group(self):
        class Fake:
            pid = 32315
            def communicate(self, timeout=None):
                if timeout is not None:
                    raise KeyboardInterrupt()
                return "partial", "cleaned"
        with patch.object(m.subprocess, "Popen", return_value=Fake()):
            with patch.object(m.os, "killpg") as killed:
                with self.assertRaises(KeyboardInterrupt):
                    m.measure(["/local/run_load.py"], 90)
        killed.assert_called_once_with(32315, m.signal.SIGKILL)

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
