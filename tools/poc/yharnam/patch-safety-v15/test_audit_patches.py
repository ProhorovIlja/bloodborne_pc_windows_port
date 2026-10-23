from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from audit_patches import audit, data_for

class PatchAuditTests(unittest.TestCase):
    def make(self, folder, name, patch_name, value, address='0x1000', enabled='true'):
        path = Path(folder) / name
        path.write_text(f'''<Patch><Metadata Name="{patch_name}" AppVer="01.09" AppElf="eboot.bin" isEnabled="{enabled}">
<PatchList><Line Type="bytes" Address="{address}" Value="{value}" /></PatchList></Metadata></Patch>''', encoding='utf-8')
        return path

    def test_collision_diff_and_same(self):
        with tempfile.TemporaryDirectory() as td:
            a = self.make(td, 'a.xml', 'A', '11223344')
            b = self.make(td, 'b.xml', 'B', '223355', '0x1001')
            d = audit([a,b])
            self.assertEqual(d['overlaps'][0]['overlap_bytes'], 3)
            self.assertEqual(d['overlaps'][0]['different_bytes'], 1)
            self.assertTrue(d['fail_closed'])
            b = self.make(td, 'b.xml', 'B', '223344', '0x1001')
            self.assertEqual(audit([a,b])['overlaps'][0]['different_bytes'], 0)
            self.assertFalse(audit([a,b])['fail_closed'])

    def test_disabled_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            a = self.make(td,'a.xml','A','F0')
            b = self.make(td,'b.xml','B','00',enabled='false')
            self.assertFalse(audit([a,b])['fail_closed'])

    def test_encoding(self):
        def line(t, v): return ET.Element('Line', {'Type':t,'Value':v})
        self.assertEqual(data_for(line('bytes16','0x9066')), b'\x66\x90')
        self.assertEqual(data_for(line('bytes','0')), b'\x00')
        self.assertEqual(data_for(line('bytes32','0x12345678')), b'\x78\x56\x34\x12')
        self.assertEqual(data_for(line('utf16','A')), b'A\x00')

    def test_broken_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            a = self.make(td, 'a.xml', 'A','11')
            a.write_text(a.read_text().replace('01.09','01.08'))
            self.assertTrue(audit([a])['fail_closed'])

if __name__=='__main__':
    unittest.main()
