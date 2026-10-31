"""Synthetic-only compiled ABI execution tests on actual Linux and Windows CPUs."""
import importlib.util
from pathlib import Path
import platform
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_189',HERE/'real_leaf_recomp_v189.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

class GeneratedNativeModuleV189Tests(unittest.TestCase):
    def test_compiled_synthetic_leaf_module_executes_via_v4_abi(self):
        if platform.system() not in ('Windows','Linux'):
            self.skipTest('native compilation tested on Windows/Linux only')
        # These are synthetic test functions; no actual user game data in CI.
        code=(b'\x31\xc0\xc3',b'\xb8\x34\x12\x00\x00\xc3',
              b'\x48\x89\xf8\xc3',b'\x89\xf8\xc3')
        sample=[(0x1000+16*i,len(op),0 if i!=1 else 0x1234,op)
                for i,op in enumerate(code)]
        with tempfile.TemporaryDirectory() as tmp:
            parent=Path(tmp)
            generated=parent/'private-generated'
            generated.mkdir()
            v.emit_private_c(generated,sample)
            if platform.system()=='Linux':
                self.assertEqual(v.check_linux_generated(generated,sample),276)
            else:
                bridge_path=HERE.parent/'recomp-v188'/'win64_coff_link_v188.py'
                bspec=importlib.util.spec_from_file_location('v188_coff',bridge_path)
                b=importlib.util.module_from_spec(bspec)
                bspec.loader.exec_module(b)
                destination=parent/'private-test.dll'
                report=b.compile_win64(generated,destination,[v.abi_dir()])
                self.assertEqual(report['source_units_compiled'],2)
                self.assertTrue(report['bb_recomp_init_export_present'])
                self.assertEqual(v.probe_compiled_library(destination,sample),276)

if __name__=='__main__':unittest.main()
