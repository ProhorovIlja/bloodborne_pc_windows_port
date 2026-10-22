"""Test ported native Hunter editor export without any real game saves."""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from scripts import save_editor as ed

def sample():
    d = bytearray(b"\x5a" * ed.SLOT_SIZE)
    d[:0x60000] = bytes(0x60000)
    struct.pack_into("<III", d, 0, 0x41, 0x18010000, 3600000)
    a = 0x10000
    d[a+1:a+13] = "Alfred".encode("utf-16le")
    struct.pack_into("<I", d, a-23, 37)
    d[a+469+34028:a+469+34032] = b"FACE"
    world = ed.EMPTY_WORLD
    a = 0x30000 + 150001
    d[a:a+len(world)] = world
    b = a + len(world)
    struct.pack_into("<fff", d, b, -196.1, -28.6, 63.4)
    c = b + 0x50
    struct.pack_into("<6I", d, 0x3c, a, len(world), b, len(world)+0x50, c, 0x200)
    d[c:c+0x200] = b"\x11" * 0x200
    struct.pack_into("<HHI", d, c+0x200, 1, 0, 0x40)
    d[c+0x208:c+0x208+0x40+27] = b"\x22" * (0x40+27)
    return bytes(d)

class NativeExport(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.user = self.root / "user"
        self.slot = self.user/"savedata_party"/"1"/"CUSA03173"/"SPRJ0005"/"userdata0002"
        self.slot.parent.mkdir(parents=True)
        self.data = sample()
        self.slot.write_bytes(self.data)
        self.dest = self.root/"editor"

    def test_editor_export_is_copy_and_import_preview_roundtrip(self):
        f = ed.export_hunter_save(self.user, "party", self.slot, self.dest)
        self.assertEqual(self.slot.read_bytes(), self.data)
        self.assertFalse(ed.world_empty(f.read_bytes()))
        self.assertEqual(ed.check_import(self.user, f)["data"], self.data)
        manifest = json.loads((self.dest/ed.MANIFEST).read_text())
        self.assertEqual(manifest["slot"], 2)
        self.assertEqual(manifest["source"], "savedata_party/1/CUSA03173/SPRJ0005/userdata0002")

    def test_refuse_other_runtime_inplace_and_existing_dest(self):
        other = self.user/"savedata_party"/"2"/"CUSA03173"/"SPRJ0005"/"userdata0002"
        other.parent.mkdir(parents=True)
        other.write_bytes(self.data)
        with self.assertRaises(ed.SaveFormatError):
            ed.export_hunter_save(self.user, "party", other, self.dest)
        with self.assertRaises(ed.SaveFormatError):
            ed.export_hunter_save(self.user, "party", self.slot, self.slot.parent)
        ed.export_hunter_save(self.user, "party", self.slot, self.dest)
        with self.assertRaises(FileExistsError):
            ed.export_hunter_save(self.user, "party", self.slot, self.dest)

    def test_refuse_untrusted_manifest_target(self):
        f = ed.export_hunter_save(self.user, "party", self.slot, self.dest)
        m = self.dest/ed.MANIFEST
        doc = json.loads(m.read_text())
        doc["source"] = "../../wrong/userdata0002"
        m.write_text(json.dumps(doc))
        with self.assertRaises(ed.SaveFormatError):
            ed.check_import(self.user, f)
        self.assertEqual(self.slot.read_bytes(), self.data)

    def test_refuse_symlinked_slot(self):
        link = self.slot.with_name("userdata0003")
        try:
            link.symlink_to(self.slot)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unsupported")
        with self.assertRaises(ed.SaveFormatError):
            ed.export_hunter_save(self.user, "party", link, self.dest)

if __name__ == "__main__":
    unittest.main()
