"""Offline XML patch collision tests. No game files or network required."""
import paths  # noqa: F401
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import patch_preflight as pp


SAMPLE = '''<?xml version="1.0"?>
<Patch>
 <Metadata Name="Performance Patch (Perf Increase)" isEnabled="true" AppVer="01.09">
  <PatchList>
   <Line Type="bytes" Address="0x100" Value="FEFF"/>
   <Line Type="bytes16" Address="0x202" Value="0x1234"/>
   <Line Type="float32" Address="0x310" Value="0.5"/>
  </PatchList>
 </Metadata>
 <Metadata Name="60 FPS++" isEnabled="true" AppVer="01.09">
  <PatchList><Line Type="bytes" Address="0x101" Value="7F01"/></PatchList>
 </Metadata>
 <Metadata Name="Identical Overlap" isEnabled="true" AppVer="01.09">
  <PatchList><Line Type="bytes" Address="0x100" Value="FE"/></PatchList>
 </Metadata>
 <Metadata Name="Opt-in Cheat" isEnabled="false" AppVer="01.09">
  <PatchList><Line Type="bytes" Address="0x102" Value="0F"/></PatchList>
 </Metadata>
</Patch>'''


class PatchPreflightTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.xml = Path(self.dir.name) / "Bloodborne.xml"
        self.xml.write_text(SAMPLE, encoding="utf-8")

    def test_supported_encoding(self):
        self.assertEqual(pp.decode_patch("bytes", "0"), b"\x00")
        self.assertEqual(pp.decode_patch("bytes", "0x0F"), b"\x0f")
        self.assertEqual(pp.decode_patch("bytes32", "0x3f800000"),
                         b"\x00\x00\x80\x3f")
        self.assertEqual(pp.decode_patch("bytes16", "0x1234"), b"\x34\x12")
        self.assertEqual(pp.decode_patch("float32", "0.5"), struct.pack("<f", 0.5))
        self.assertEqual(pp.decode_patch("utf16", "abc"), "abc".encode("utf-16le"))
        with self.assertRaises(ValueError):
            pp.decode_patch("bytes", "not-hex")

    def test_default_scan_has_one_real_collision(self):
        report = pp.audit([self.xml], defaults=True)
        self.assertEqual(len(report["conflicts"]), 1)
        collision = report["conflicts"][0]
        self.assertEqual(collision["ranges"], [["0x101", "0x101"]])
        self.assertEqual(collision["different_bytes"], 1)
        self.assertNotIn("Opt-in Cheat", report["patch_sets"])
        self.assertFalse(report["safe_to_apply"])

    def test_explicit_patch_selection_resolves_collision(self):
        report = pp.audit([self.xml], enabled_names={"Performance Patch (Perf Increase)"})
        self.assertEqual(report["conflicts"], [])
        self.assertTrue(report["safe_to_apply"])
        self.assertEqual(report["selected_write_lines"], 3)
        self.assertEqual(pp.audit([self.xml], defaults=True)["patch_sets"][-1], "Performance Patch (Perf Increase)")

    def test_disjoint_address_spaces_and_identical_bytes_not_conflicts(self):
        writes = [
            pp.PatchWrite("A", "Bloodborne.xml", 0x100, b"\x01\x02"),
            pp.PatchWrite("B", "Bloodborne.xml", 0x100, b"\x01"),
            pp.PatchWrite("C", "DollRebirth.xml", 0x500, b"\x01"),
        ]
        self.assertEqual(pp.find_conflicts(writes), [])

    def test_conflicts_group_adjacent_byte_addresses(self):
        writes = [
            pp.PatchWrite("A", "x.xml", 0x100, b"\x00\x00\x00"),
            pp.PatchWrite("B", "x.xml", 0x100, b"\x01\x01\x01"),
        ]
        c = pp.find_conflicts(writes)
        self.assertEqual(c[0]["ranges"], [["0x100", "0x102"]])
        self.assertEqual(c[0]["different_bytes"], 3)

    def test_rejects_large_or_broken_xml(self):
        self.xml.write_text("<Patch><", encoding="utf-8")
        with self.assertRaises(pp.ET.ParseError):
            pp.audit([self.xml], defaults=True)


if __name__ == "__main__":
    unittest.main()
