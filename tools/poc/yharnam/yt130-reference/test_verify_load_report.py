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


    def test_refused_counts_retries_not_unique_hunters(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"load.jsonl"
            p.write_text(json.dumps(self.baseline()|{"refused":1174})+"\n")
            self.assertEqual(mod.load(p,200)["refused"],1174)

if __name__=="__main__":
    unittest.main()
