# SPDX-License-Identifier: GPL-2.0-or-later
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from switch_v505 import emit, plan


class TestSwitch(unittest.TestCase):
    def test_native_routes_without_table_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'synthetic-table.bin'
            original.write_bytes(struct.pack('<iii', -16, 20, -16))
            ids = plan(original.read_bytes(), 256, {240, 276})
            self.assertEqual(ids, (240, 276, 240))
            source = root / 'fixture.c'
            source.write_text(emit(ids) + '''
int main(void) {
    uint64_t id=0;
    if(!switch_route(0,&id)||id!=240)return 1;
    if(!switch_route(1,&id)||id!=276)return 2;
    if(!switch_route(2,&id)||id!=240)return 3;
    if(switch_route(3,&id)||switch_route(SIZE_MAX,&id)||switch_route(0,0)||id!=240)return 4;
    return 0;
}
''', encoding='ascii')
            exe = root / 'fixture.exe'
            subprocess.run([os.environ.get('CC', 'clang'), '-std=c11', '-O2', '-Wall', '-Wextra',
                            '-Werror', str(source), '-o', str(exe)], check=True)
            original.unlink()
            source.unlink()
            subprocess.run([str(exe)], cwd=root, check=True)

    def test_invalid_input_fails_before_emission(self):
        for raw, base, allowed in [(b'', 0, set()), (b'\0', 0, {0}), (bytes(16388), 0, {0}),
                                   (struct.pack('<i', -1), 0, {-1}),
                                   (struct.pack('<i', 1), (1 << 64) - 1, {1 << 64}),
                                   (struct.pack('<ii', 1, 2), 0, {1})]:
            with self.subTest(base=base, length=len(raw)), self.assertRaises(ValueError):
                plan(raw, base, allowed)
        for bad in [(), (-1,), (1 << 64,), (True,)]:
            with self.assertRaises(ValueError):
                emit(bad)
