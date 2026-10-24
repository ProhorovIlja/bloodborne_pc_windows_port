"""Offline and CLI regression tests for native Bloodborne resource trends; no retail game needed."""
from datetime import datetime, timezone, timedelta
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "tools/diagnostics/process_memory_report.py"
SPEC = importlib.util.spec_from_file_location("process_memory_report", SCRIPT)
mem = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mem
SPEC.loader.exec_module(mem)
BASE = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)


def csv_rows(private=(200, 260, 350), handles=(200, 260, 310), *,
             pid=900, per_phase=6, seconds_step=15, start=BASE):
    lines = [",".join(mem.FIELDS)]
    for i in range(3 * per_phase):
        group = i // per_phase
        tm = (start + timedelta(seconds=i * seconds_step)).isoformat()
        p = round((private[group] + (i % per_phase) * 0.1) * mem.MiB)
        h = handles[group] + i % per_phase
        lines.append(
            f"{tm},{pid},{start.isoformat()},{p},{round(p * 0.7)},"
            f"{p * 3},{h},12"
        )
    return "\n".join(lines) + "\n"


class MemoryReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def file(self, data, name="observations.csv"):
        path = self.dir / name
        path.write_text(data, encoding="utf-8")
        return path

    def test_progressive_memory_growth(self):
        report = mem.analyze(self.file(csv_rows()))
        self.assertEqual(report.process_lifetimes, 1)
        self.assertTrue(report.suspicious_growth)
        self.assertEqual(report.processes[0].samples, 18)
        self.assertGreater(report.processes[0].private_growth_mib, 140)
        self.assertGreater(report.processes[0].handle_growth, 100)

    def test_stable_process_not_flagged(self):
        report = mem.analyze(self.file(csv_rows(private=(250, 250, 250),
                                                 handles=(200, 200, 200))))
        self.assertFalse(report.suspicious_growth)

    def test_spike_in_middle_is_not_sustained(self):
        report = mem.analyze(self.file(csv_rows(private=(250, 900, 250),
                                                 handles=(200, 1000, 200))))
        self.assertFalse(report.suspicious_growth)

    def test_memory_growth_below_threshold_not_flagged(self):
        report = mem.analyze(self.file(csv_rows(private=(200, 205, 215),
                                                 handles=(200, 201, 205))))
        self.assertFalse(report.suspicious_growth)

    def test_process_restart_separated_even_with_same_pid(self):
        first = csv_rows(per_phase=4)
        later = csv_rows(private=(250, 250, 250), handles=(50, 50, 50),
                         per_phase=4, start=BASE + timedelta(hours=1))
        report = mem.analyze(self.file(first + "\n".join(later.splitlines()[1:]) + "\n"))
        self.assertEqual(report.process_lifetimes, 2)
        self.assertEqual(sorted(p.samples for p in report.processes), [12, 12])

    def test_multiple_simultaneous_clients_are_separate(self):
        a = csv_rows(pid=123)
        b = csv_rows(private=(300, 300, 300), handles=(200, 200, 200), pid=234)
        report = mem.analyze(self.file(a + "\n".join(b.splitlines()[1:]) + "\n"))
        self.assertEqual(report.process_lifetimes, 2)
        self.assertTrue(report.suspicious_growth)
        self.assertTrue(next(x for x in report.processes if x.pid == 123).suspicious_growth)
        self.assertFalse(next(x for x in report.processes if x.pid == 234).suspicious_growth)

    def test_short_session_cannot_prove_growth(self):
        report = mem.analyze(self.file(csv_rows(seconds_step=2)))
        self.assertFalse(report.suspicious_growth)
        self.assertIn("Less than two minutes", " ".join(report.processes[0].notes))

    def test_too_few_samples_fail_closed_when_requested(self):
        report = mem.analyze(self.file(csv_rows(per_phase=2)))
        self.assertFalse(report.suspicious_growth)
        self.assertIsNone(report.processes[0].early)

    def test_unexpected_csv_columns_rejected(self):
        with self.assertRaises(mem.BadSample):
            mem.analyze(self.file("pid,private_bytes\n1,200\n"))

    def test_negative_counters_rejected(self):
        data = csv_rows().replace(",200,", ",-200,", 1)
        with self.assertRaises(mem.BadSample):
            mem.analyze(self.file(data))

    def test_naive_datetime_rejected(self):
        data = csv_rows().replace("+00:00", "", 1)
        with self.assertRaises(mem.BadSample):
            mem.analyze(self.file(data))

    def test_samples_before_start_rejected(self):
        data = csv_rows()
        first = data.splitlines()
        fields = first[1].split(",")
        fields[0] = (BASE - timedelta(seconds=5)).isoformat()
        first[1] = ",".join(fields)
        with self.assertRaises(mem.BadSample):
            mem.analyze(self.file("\n".join(first) + "\n"))

    def test_wrong_csv_width_rejected(self):
        data = csv_rows() + "broken,record\n"
        with self.assertRaises(mem.BadSample):
            mem.analyze(self.file(data))

    def test_cli_json_and_exit_on_growth(self):
        path = self.file(csv_rows())
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(path), "--json", "--fail-on-growth"],
            text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 3, result.stderr)
        doc = json.loads(result.stdout)
        self.assertTrue(doc["suspicious_growth"])
        self.assertEqual(doc["processes"][0]["pid"], 900)

    def test_cli_short_samples_fail_closed_even_with_valid_row_count(self):
        path = self.file(csv_rows(seconds_step=2))
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(path), "--fail-on-growth", "--json"],
            text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 3)
        self.assertFalse(json.loads(result.stdout)["suspicious_growth"])

    def test_cli_stable_exit_zero(self):
        path = self.file(csv_rows(private=(250, 250, 250), handles=(200, 200, 200)))
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(path), "--fail-on-growth"],
            text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_missing_file_returns_error_two(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.dir / "absent.csv")],
            text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 2)

    def test_collector_source_only_reads_os_process_properties(self):
        source = (ROOT / "tools/diagnostics/collect_process_memory.ps1").read_text(encoding="utf-8")
        self.assertIn("Get-Process -Name $ProcessName", source)
        self.assertIn("Get-Process -Id $ProcessId", source)
        self.assertIn("PrivateMemorySize64", source)
        self.assertIn("WorkingSet64", source)
        self.assertIn("HandleCount", source)
        self.assertIn("[string]$ProcessName = 'bb-probe'", source)
        self.assertNotIn("ReadProcessMemory", source)


if __name__ == "__main__":
    unittest.main()
