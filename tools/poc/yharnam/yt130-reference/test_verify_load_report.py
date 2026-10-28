"""Test report validation with synthetic numbers, not benchmark claims."""
import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

f=Path(__file__).with_name("verify_load_report.py")
spec=importlib.util.spec_from_file_location("load_check",f)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ValidatorTests(unittest.TestCase):
    def baseline(self):
        x={k:1 for k in mod.KEYS}
        x.update(players=200,playing=180,refused=20,packets_sent=1000,
                 packets_received=950,packets_lost=50)
        return x

    def test_one_valid_summary(self):
        with TemporaryDirectory() as d:
            f=Path(d)/"load.jsonl"
            f.write_text("console log\n"+json.dumps(self.baseline())+"\n")
            self.assertEqual(mod.load(f,200)["playing"],180)

    def test_fail_closed_no_report_fabrication(self):
        with TemporaryDirectory() as d:
            f=Path(d)/"load.jsonl"
            for r in (
                self.baseline()|{"players":199},
                self.baseline()|{"packets_sent":0},
                self.baseline()|{"playing":201},
                self.baseline()|{"playing":0},
                self.baseline()|{"server_cpu_avg":-1},
                self.baseline()|{"server_in_mbit":"n/a"},
            ):
                f.write_text(json.dumps(r)+"\n")
                with self.subTest(report=r),self.assertRaises(ValueError):
                    mod.load(f,200)
            f.write_text(json.dumps(self.baseline())+"\n"+json.dumps(self.baseline()))
            with self.assertRaises(ValueError):
                mod.load(f,200)


    def test_four_player_smoke_must_include_actual_delivery_not_only_playing(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "smoke.jsonl"
            full = self.baseline() | {
                "players": 4, "playing": 4, "refused": 0,
                "packets_sent": 1948, "packets_received": 1948,
                "packets_lost": 0, "udp_buffer_drops": 0,
                "relay_ms_p99": 0.4
            }
            p.write_text(json.dumps(full) + "\n")
            self.assertEqual(mod.load(p, 4, require_full_gameplay=True)["playing"], 4)
            partial = full | {"packets_sent": 2091, "packets_received": 264}
            p.write_text(json.dumps(partial) + "\n")
            # This is precisely the false green reported by PR45.
            self.assertEqual(mod.load(p, 4)["playing"], 4)
            with self.assertRaises(ValueError):
                mod.load(p, 4, require_full_gameplay=True)
            for bad in (
                full | {"playing": 3},
                full | {"packets_lost": 1},
                full | {"udp_buffer_drops": 1},
                full | {"relay_ms_p99": 51},
                full | {"packets_received": 1928},
                full | {"packets_sent": 1, "packets_received": 1}
            ):
                with self.subTest(bad=bad):
                    p.write_text(json.dumps(bad) + "\n")
                    with self.assertRaises(ValueError):
                        mod.load(p, 4, require_full_gameplay=True)

    def test_refused_counts_retries_not_unique_hunters(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"load.jsonl"
            p.write_text(json.dumps(self.baseline()|{"refused":1174})+"\n")
            self.assertEqual(mod.load(p,200)["refused"],1174)

if __name__=="__main__":
    unittest.main()
