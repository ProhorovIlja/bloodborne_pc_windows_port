"""V182: no-game original Qt socket capacity telemetry regression tests."""
import importlib.util
import os
from pathlib import Path
import re
import tempfile
from textwrap import dedent
import unittest

p=Path(__file__).with_name("stage_udp_buffer_readback_report_v182.py")
spec=importlib.util.spec_from_file_location("qt_udp_v182",p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def fixture():
    return "\n".join((
        "# SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS",
        "# SHYT_V174_ORIGINAL_QT_POLICY_FILTER_JSON",
        mod.BEFORE,mod.ROW_OLD,mod.TOTAL_OLD,
    ))

class QtUdpReadbackV182Tests(unittest.TestCase):
    def test_exact_source_and_idempotence(self):
        code=mod.patch(fixture())
        self.assertIn(mod.MARK,code)
        self.assertIn('"udp_socket_readback_complete":',code)
        self.assertIn('"udp_socket_min_effective_receive_bytes":',code)
        self.assertIn("NOT per-socket packet losses or production QoS",code)
        for name in ("online_id","packet_payload","authorization","sender_ip"):
            self.assertNotIn(name,mod.AFTER+mod.ROW_NEW+mod.TOTAL_NEW)
        with self.assertRaisesRegex(ValueError,"expects"):
            mod.patch(code)
        with self.assertRaisesRegex(ValueError,"expects"):
            mod.patch(fixture().replace("SHYT_V174_ORIGINAL_QT_POLICY_FILTER_JSON","DRIFT"))

    def test_readbacks_from_one_server_bind_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"shard0"
            folder.mkdir()
            f=folder/"shadnet.log"
            f.write_text(
                "Link UDP socket buffers requested_bytes=16777216 "
                "effective_receive_bytes=425984 effective_send_bytes=425984\n"
                "Private user name not collected\n",encoding="utf-8")
            program=dedent(mod.AFTER.split("        per_shard = []")[0])
            env={"re":re,"os":os,"root":tmp}
            exec(program,env)
            read=env["socket_buffers"]
            self.assertEqual(read(0),(16777216,425984,425984,1,True))
            self.assertEqual(mod.patch(fixture()).count("socket_buffers(i)"),1)
            self.assertNotIn("Private user",str(read(0)))
            f.write_text("",encoding="utf-8")
            self.assertEqual(read(0),(0,0,0,0,False))
            f.write_text(
                "Link UDP socket buffers requested_bytes=16777216 "
                "effective_receive_bytes=425984 effective_send_bytes=425984\n"*2,encoding="utf-8")
            self.assertEqual(read(0),(16777216,425984,425984,2,False))

    def test_invalid_and_unbounded_bind_reports_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"shard0"
            folder.mkdir()
            f=folder/"shadnet.log"
            program=dedent(mod.AFTER.split("        per_shard = []")[0])
            env={"re":re,"os":os,"root":tmp}
            exec(program,env)
            for payload in (
                "Link UDP socket buffers requested_bytes=16777216 "
                "effective_receive_bytes=0 effective_send_bytes=1024\n",
                "Link UDP socket buffers requested_bytes=16777216 "
                "effective_receive_bytes=2147483648 effective_send_bytes=1024\n",
                ("Link UDP socket buffers requested_bytes=16777216 "
                 "effective_receive_bytes=425984 effective_send_bytes=425984\n")*9,
            ):
                f.write_text(payload,encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError,"(invalid|too many)"):
                    env["socket_buffers"](0)

    def test_still_one_original_shard_source_file(self):
        self.assertEqual(mod.FILE,"server/loadtest/run_shards.py")
        self.assertEqual(mod.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertNotIn("SHYT_ENABLE_TEST_LOCAL_MTLS",mod.AFTER)
        self.assertNotIn("sysctl",mod.AFTER)

if __name__=="__main__":unittest.main()
