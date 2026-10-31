"""V149: smoke-test YT1.3's REAL Windows native run.py without game bytes.

The preceding V148 guard protects Visy bbport.exe, not original YT run.py.
The actual YT native Windows flow is run.py -> bb-probe.exe + prepared SELF.
This test pins original YT run.py, creates only a FAKE empty file to allow
the launcher's source path selection, and verifies missing-game fail closed
before ever invoking native code or making network connections.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
RUN_BLOB="1880007c0359de018bc61f46bc2a71902afe129b"
ROOT=Path(__file__).resolve().parents[2]


class RealYT130NativeEntrypoint(unittest.TestCase):
    def source(self) -> Path:
        base=os.environ.get("SHYT_V149_ORIGINAL_BBPORT")
        if not base:
            self.skipTest("original YT1.3 checkout not supplied by pinned CI")
        return Path(base).resolve()

    def test_exact_upstream_windows_launch_source(self):
        root=self.source()
        run=root/"run.py"
        self.assertTrue(run.is_file())
        raw=run.read_bytes().replace(b"\r\n",b"\n")
        blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
        self.assertEqual(blob,RUN_BLOB)
        data=raw.decode("utf-8")
        self.assertIn("bb-probe.exe not found:",data)
        self.assertIn("if not (game / 'eboot.bin').is_file():",data)
        self.assertIn("online_overrides(env, user_dir)",data)
        self.assertIn("BB_ONLINE",data)
        self.assertIn("boot-linked.bin",data)
        self.assertIn("SHADPS4_HTTP_HOST_OVERRIDES_JSON",data)
        self.assertNotIn("out/bbport.exe",data)
        self.assertNotIn("BB_PARTY=host",data)
    def test_original_upstream_rejects_missing_game_before_native_exe_launch(self):
        root=self.source()
        with TemporaryDirectory() as temp:
            p=Path(temp)
            fake_binary=p/"NO_REAL_BINARY_bb-probe.exe"
            fake_binary.write_bytes(b"synthetic-not-executable")
            game=p/"NO_GAME_FILES"
            game.mkdir()
            private_data=p/"DATA"
            private_data.mkdir()
            env=os.environ.copy()
            for name in ("BB_ONLINE","BB_PARTY","BB_GAME_DIR","BB_DATA_DIR","BB_PROBE",
                         "SHADPS4_HTTP_HOST_OVERRIDES_JSON","BB_COMMUNITY_SERVER"):
                env.pop(name,None)
            env.update({"BB_GAME_DIR":str(game),"BB_DATA_DIR":str(private_data),
                        "BB_PROBE":str(fake_binary), "BB_ONLINE":"0",
                        "PYTHONIOENCODING":"utf-8"})
            result=subprocess.run([sys.executable,str(root/"run.py")],
                                  cwd=root,env=env,
                                  capture_output=True,text=True,errors="replace",
                                  timeout=15)
            # The dummy binary cannot be executed. The input validation must
            # stop before ever reaching Process/CreateProcess.
            combined=result.stdout+result.stderr
            self.assertNotEqual(result.returncode,0)
            self.assertIn("No eboot.bin",combined)
            self.assertNotIn("synthetic-not-executable",combined)
            self.assertFalse((private_data/"user").exists())
            self.assertFalse((game/"eboot.bin").exists())


if __name__=="__main__":
    unittest.main()
