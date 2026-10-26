import importlib.util
from pathlib import Path
import unittest
f=Path(__file__).with_name("prepare_synthetic_load.py")
s=importlib.util.spec_from_file_location("yt_loadsetup",f)
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)
class TestPinnedLoad(unittest.TestCase):
    def test_argv_is_one_original_coop_protocol_fingerprint(self):
        m.check_argv()
        self.assertEqual(m.FINGERPRINT,"bb-build 1;version=dev;protocol=9;")
    def test_refuse_unpinned_synthetic_source(self):
        with self.assertRaisesRegex(ValueError,"pinned"):
            m.transform(b"not official release v1.3 script")
if __name__=="__main__":
    unittest.main()
