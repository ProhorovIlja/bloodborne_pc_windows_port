import importlib.util
from pathlib import Path
import tempfile
import unittest

S=importlib.util.spec_from_file_location('check_v188',Path(__file__).with_name('check_upstream_v188.py'))
m=importlib.util.module_from_spec(S)
S.loader.exec_module(m)

class PinnedRecompilerGuardTests(unittest.TestCase):
    def test_original_source_contract_and_reject_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for p in ['tools/recomp/bbrecomp.c','tools/recomp/build_library.py','src/recomp/rc.h']:
                f=root/p
                f.parent.mkdir(parents=True,exist_ok=True)
                text={'bbrecomp.c':'/* emit */ visibility(default) RcFunction bb_recomp_init(const RcApi *api, size_t *count) { };',
                      'build_library.py':'--target=arm64-apple-macos15 \n ld64.lld / fake',
                      'rc.h':'#define BB_RECOMP_API_VERSION 4u \n' + '/* public struct */'}[f.name]
                f.write_text(text + (" " * 128))
            self.assertTrue(m.guard(root)['win64_pe_coff_linker_adapter_needed'])
            (root/'tools/recomp/build_library.py').write_text('windows ready' + ' '*128)
            with self.assertRaisesRegex(ValueError,'changed'):
                m.guard(root)
            (root/'tools/recomp/build_library.py').write_text('ld64.lld --target=arm64-apple-macos15' + ' '*128)
            (root/'src/recomp/rc.h').write_text('#define BB_RECOMP_API_VERSION 5u' + ' '*128)
            with self.assertRaisesRegex(ValueError,'ABI changed'):
                m.guard(root)
if __name__=='__main__':unittest.main()
