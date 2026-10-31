import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parent
s = importlib.util.spec_from_file_location('win64v188', ROOT/'win64_coff_link_v188.py')
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)

class Win64RecompCodegenTests(unittest.TestCase):
    def test_real_fixture_is_generated_named_and_two_units(self):
        files = m.sources_in(ROOT/'fixtures')
        self.assertEqual([f.name for f in files], ['recomp.c','recomp_1.c'])
        self.assertIn('__attribute__((visibility("default")))', files[0].read_text())
        self.assertNotIn('RC_EXPORT', files[0].read_text())
        self.assertNotIn('__declspec(dllexport)', files[0].read_text())

    def test_fail_closed_symlinks_duplicate_and_excess_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            (d/'recomp.c').write_text('ok')
            (d/'recomp_1.c').write_text('ok')
            if os.name != 'nt':
                (d/'recomp_2.c').symlink_to(d/'recomp_1.c')
                with self.assertRaises(m.BuildError): m.sources_in(d)
                (d/'recomp_2.c').unlink()
            (d/'recomp.c').unlink()
            with self.assertRaises(m.BuildError): m.sources_in(d)

    def test_no_partial_output_after_link_failure(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'incomplete.dll'
            with patch.object(m.shutil,'which',return_value='/fake/clang'),patch.object(m,'run_command',side_effect=m.BuildError('private failure')):
                with self.assertRaisesRegex(m.BuildError,'private failure'):
                    m.compile_win64(ROOT/'fixtures',out,[ROOT.parent/'native_recomp_bridge_v187'])
            self.assertFalse(out.exists())

    def test_requires_external_output_and_no_shell(self):
        with self.assertRaisesRegex(m.BuildError,'inside private'):
            with patch.object(m.shutil,'which',return_value='/fake'):
                m.compile_win64(ROOT/'fixtures',ROOT/'fixtures'/'out.dll',[ROOT])
        import inspect
        src=inspect.getsource(m.run_command)
        self.assertIn('capture_output=True',src)
        self.assertNotIn('shell=True',src)

    def test_broken_pe_header_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.dll'
            p.write_bytes(b'X'*1024)
            with self.assertRaisesRegex(m.BuildError,'PE'):
                m.read_pe_exports(p)
            p.write_bytes(b'MZ'+b'\0'*1022)
            with self.assertRaisesRegex(m.BuildError,'PE'):
                m.read_pe_exports(p)

if __name__=='__main__': unittest.main()
