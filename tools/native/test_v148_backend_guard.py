"""V148: original Windows native launcher must never silently fake YT Protocol8."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
BATCH=ROOT/"run.bat"

class NativeOnlineBackendGuardTests(unittest.TestCase):
    def test_native_windows_backend_preflight_occurs_after_settings_before_saves(self):
        source=BATCH.read_text(encoding="utf-8")
        settings=source.index("REM Started without the launcher: apply its last saved settings")
        marker=source.index("REM SHYT-V148 native Windows backend guard.")
        user_dirs=source.index("REM Writable directory for generated files")
        self.assertLess(settings,marker)
        self.assertLess(marker,user_dirs)
        self.assertEqual(source.count("REM SHYT-V148 native Windows backend guard."),1)
        self.assertIn('set "native_online_check=%BB_ONLINE: =%"',source)
        self.assertIn('if not "%native_online_check%"=="" goto native_backend_not_ready',source)
        self.assertIn('if /i "%native_backend_check%"=="party" (',source)
        self.assertIn('if /i "%native_backend_check%"=="offline" (',source)
        self.assertIn('if /i "%native_backend_check%"=="auto" goto native_backend_ok',source)
        self.assertEqual(source.count("exit /b 22"),2)
        self.assertIn("different network protocol and save format",source)
        self.assertNotIn("BB_ONLINE=1",source)
    @unittest.skipUnless(sys.platform=="win32","Batch runtime test needs Windows")
    def test_windows_cmd_rejects_unsupported_and_conflicting_modes_before_game(self):
        cases=(
            {"BB_ONLINE":"1"},
            {"BB_ONLINE":"true","BB_PARTY":"host"},
            {"BB_NATIVE_BACKEND":"yt"},
            {"BB_NATIVE_BACKEND":"yharnam_together"},
            {"BB_NATIVE_BACKEND":"party"},
            {"BB_NATIVE_BACKEND":"offline","BB_PARTY":"host"},
            {"BB_NATIVE_BACKEND":"party","BB_PARTY":"off"},
        )
        for opt in cases:
            with self.subTest(mode=opt):
                env=os.environ.copy()
                for name in ("BB_ONLINE","BB_PARTY","BB_NATIVE_BACKEND"):
                    env.pop(name,None)
                env.update(opt)
                env.update({"PYTHON":sys.executable,"BB_FROM_LAUNCHER":"1",
                            "BB_NO_LAUNCHER_SETTINGS":"1"})
                p=subprocess.run(["cmd.exe","/d","/c",str(BATCH)],cwd=ROOT,env=env,
                    capture_output=True,text=True,errors="replace",timeout=20)
                self.assertEqual(p.returncode,22,
                    "Expected early unsupported/contradictory native protocol error; "+
                    p.stdout[-400:]+p.stderr[-200:])
                self.assertIn("Native Windows backend",p.stdout)
    def test_existing_offline_and_native_party_paths_are_still_reachable(self):
        source=BATCH.read_text(encoding="utf-8")
        # Both offline and native host/join fall through to existing
        # game-data preparation; exact runtime success requires real assets.
        self.assertIn(':native_backend_ok\nset "native_online_check="',source)
        self.assertIn('if "%native_backend_check%"=="" goto native_backend_ok',source)
        self.assertIn('if /i "%native_backend_check%"=="auto" goto native_backend_ok',source)
        self.assertIn('if not defined BB_PARTY goto native_backend_conflict',source)

if __name__=="__main__":
    unittest.main()
