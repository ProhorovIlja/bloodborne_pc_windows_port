"""V155 Qt original server Data wire kind=3 diagnostics; no payload or IP logs."""
import importlib.util
import os
from pathlib import Path
import re
import tempfile
import textwrap
import unittest

path=Path(__file__).with_name("stage_shard_wire_v155.py")
spec=importlib.util.spec_from_file_location("yt130_shard_wire_v155",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def original_v117_fixture():
    return (
        "import shutil\nimport shlex\nimport socket\n"+
        m.V117+"\n"+
        "def main():\n"+
        m.READER_ANCHOR+
        "            row = next((s for s in region.get('shards', []) if s.get('name') == f'lt-{i}'), {})\n"+
        "            per_shard.append({\n                \"shard\": f\"lt-{i}\",\n"+
        m.ROW_ANCHOR+
        "\n            })\n"+
        "        print(json.dumps({\n"+
        m.SUMMARY_ANCHOR+
        "\n"
    )


class ActualQtWireDiagnosticsTests(unittest.TestCase):
    def test_pins_existing_real_Qt_server_and_five_hunter_generator(self):
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.PATH.as_posix(),"server/loadtest/run_shards.py")
        self.assertIn("SHYT-V117-TRUE-FIVE-HUNTER",m.V117)
        self.assertIn("YT130_WIRE_TRAFFIC",m.READER_PATCH)
        self.assertIn("kind=3",m.READER_PATCH)
        self.assertIn("wire_counter_scope",m.SUMMARY_PATCH)
        self.assertNotIn("payload=",m.READER_PATCH)
        self.assertNotIn("ip=",m.READER_PATCH.lower())
    def test_staging_preserves_existing_shard_cpu_and_game_counters(self):
        staged=m.patch_source(original_v117_fixture())
        self.assertIn("import re\nimport socket",staged)
        self.assertIn("game_wire_in_packets",staged)
        self.assertIn("game_wire_out_packets",staged)
        self.assertIn("game_wire_sample_windows",staged)
        self.assertIn("link_thread_cpu_avg",staged)
        self.assertIn("SHYT-V117-TRUE-FIVE-HUNTER",staged)
        self.assertEqual(staged.count("data_wire(i)"),1)
        with self.assertRaisesRegex(ValueError,"cannot stage twice"):
            m.patch_source(staged)
        for token in (m.IMPORT_ANCHOR,m.READER_ANCHOR,m.ROW_ANCHOR,m.SUMMARY_ANCHOR):
            with self.subTest(token=token[:38]):
                with self.assertRaisesRegex(ValueError,"original source drift"):
                    m.patch_source(original_v117_fixture().replace(token,"BROKEN"))
        with self.assertRaisesRegex(ValueError,"prior exact original V117"):
            m.patch_source(original_v117_fixture().replace(m.V117,"BROKEN"))
    def test_true_qt_wire_log_parser_counts_no_client_identifiers(self):
        # Execute the EXACT generated source of the reader, not a second
        # independently reimplemented pattern.
        body=m.READER_PATCH.split("\n        per_shard = []",1)[0]
        with tempfile.TemporaryDirectory(prefix="yt-v155-private-") as home:
            root=Path(home)
            for i in range(2):
                (root/f"shard{i}").mkdir()
            (root/"shard0"/"shadnet.log").write_text(
                "irrelevant auth user=SECRET_USER token=SECRET\n"
                "YT130_WIRE_TRAFFIC kind=3 in_packets=300 in_bytes=19000 out_packets=900 out_bytes=57000\n"
                "YT130_WIRE_TRAFFIC kind=8 in_packets=555 in_bytes=2000 out_packets=555 out_bytes=2000\n"
                "YT130_WIRE_TRAFFIC kind=3 in_packets=25 in_bytes=1499 out_packets=75 out_bytes=4559\n")
            (root/"shard1"/"shadnet.log").write_text(
                "YT130_WIRE_TRAFFIC kind=3 in_packets=1000 in_bytes=64000 out_packets=2990 out_bytes=196000\n"
                "YT130_WIRE_TRAFFIC kind=3 in_packets=9x in_bytes=12 out_packets=30 out_bytes=60\n")
            env={"os":os,"re":re,"root":str(root)}
            exec(textwrap.dedent(body),env)
            counts0=env["data_wire"](0)
            counts1=env["data_wire"](1)
            self.assertEqual(counts0,(325,975,20499,61559,2))
            self.assertEqual(counts1,(1000,2990,64000,196000,1))
            self.assertEqual(tuple(a+b for a,b in zip(counts0,counts1)),
                             (1325,3965,84499,257559,3))
    def test_per_shard_missing_log_fails_closed(self):
        body=m.READER_PATCH.split("\n        per_shard = []",1)[0]
        with tempfile.TemporaryDirectory() as root:
            env={"os":os,"re":re,"root":root}
            exec(textwrap.dedent(body),env)
            with self.assertRaises(FileNotFoundError):
                env["data_wire"](0)

if __name__=="__main__":
    unittest.main()
