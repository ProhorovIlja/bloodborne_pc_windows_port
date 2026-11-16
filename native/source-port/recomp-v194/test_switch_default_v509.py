# SPDX-License-Identifier: GPL-2.0-or-later
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from switch_v505 import emit_u32


class TestSwitchDefault(unittest.TestCase):
    def test_unsigned_bounds_and_distinct_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'route.c'
            exe = Path(tmp) / 'route.exe'
            source.write_text(emit_u32((240, 276, 240), 292) + '''
int main(void) {
    for (uint32_t i=0;i<256;++i) {
        uint64_t expected=i==1?276:i<3?240:292;
        if(bb_switch_u32(i)!=expected)return 1;
    }
    return bb_switch_u32(UINT32_MAX)!=292 || bb_switch_u32(UINT32_C(0x80000000))!=292;
}
''', encoding='ascii')
            subprocess.run([os.environ.get('CC', 'clang'), '-std=c11', '-O2', '-Wall', '-Wextra',
                            '-Werror', str(source), '-o', str(exe)], check=True)
            source.unlink()
            subprocess.run([str(exe)], cwd=tmp, check=True)

    def test_invalid_default(self):
        for bad in (-1, 1 << 64, True):
            with self.assertRaises(ValueError):
                emit_u32((240,), bad)
