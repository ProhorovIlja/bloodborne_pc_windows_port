import unittest, sys, pathlib, ast
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import patch_and_freeze as p

class LauncherTests(unittest.TestCase):
    def test_ports(self):
        before = "import os\n" + p.PORT_LINE + "\n" + p.COOP_UPDATES + "\n    pass\n"
        after = p.patch_coop(before)
        self.assertIn("32313, 32315, 32314, 21443", after)
        self.assertIn("return []", after)
        ast.parse(after)
        with self.assertRaises(ValueError): p.patch_coop(after)

    def test_isolated_profile(self):
        before = "CONFIG_DIR = Path('x') / " + p.PROFILE_LINE + "\n" + p.NORMAL_UPDATES + "\n    pass\n" + "APP_DEFAULTS = {'check_updates': True, 'animations': True}\n"
        after = p.patch_launcher(before)
        self.assertIn("bbport-launcher-coop-shpoc", after)
        self.assertIn("'check_updates': False", after)
        self.assertIn("return None", after)
        ast.parse(after)

    def test_no_dev_tools_needed(self):
        code = (ROOT / "INSTALL-POC.ps1").read_text("utf-8")
        self.assertNotIn("pip install", code)
        self.assertNotIn("git clone", code)
        self.assertIn("OpenFileDialog", code)
        self.assertIn("BLauncher.exe", code)
        self.assertIn("robocopy.exe", code)
        self.assertNotIn("Stop-Service", code)

if __name__ == "__main__":
    unittest.main()
