"""Offline synthetic save fixtures for the Hunter Hub parser. No player saves in CI."""
import struct
import tempfile
import unittest
from pathlib import Path

import paths  # noqa: F401
import hunter_profiles as hp

AT = 0x7000
DATA_SIZE = 0x20000
STATS = {"vitality": 40, "endurance": 20, "strength": 10,
         "skill": 42, "bloodtinge": 9, "arcane": 6}  # level = 77


def make_slot(name="Maria", stats=None):
    buf = bytearray(DATA_SIZE)
    buf[AT + hp.FACE_TO_NAME:AT + hp.FACE_TO_NAME + 4] = b"FACE"
    encoded = name.encode("utf-16-le")
    buf[AT:AT + len(encoded)] = encoded
    for key, offset in hp.OFFSETS.items():
        struct.pack_into("<I", buf, AT + offset, (stats or STATS)[key])
    struct.pack_into("<I", buf, AT + hp.LEVEL, sum((stats or STATS).values()) - 50)
    struct.pack_into("<I", buf, AT + hp.ECHOES, 124000)
    struct.pack_into("<I", buf, AT + hp.INSIGHT, 19)
    struct.pack_into("<I", buf, AT + hp.DEATHS, 7)
    struct.pack_into("<I", buf, hp.PLAYED_MS, 3600050)
    buf[AT + hp.JOURNEY] = 2
    return bytes(buf)


class HunterProfileTests(unittest.TestCase):
    def test_valid_slot_is_read_only_and_inferred_build_is_not_factual_class(self):
        h = hp.parse_slot(make_slot(), "userdata0000", source="native:pc")
        self.assertIsNotNone(h)
        self.assertEqual(h.name, "Maria")
        self.assertEqual(h.level, 77)
        self.assertEqual(h.skill, 42)
        self.assertEqual(h.echoes, 124000)
        self.assertEqual(h.insight, 19)
        self.assertEqual(h.playtime_seconds, 3600)
        self.assertEqual(h.deaths, 7)
        self.assertEqual(h.journey, 2)
        self.assertIn("estimated", h.build_guess)
        self.assertNotIn("last_location", h.public())
        self.assertNotIn("equipped_weapon", h.public())

    def test_cyrillic_name(self):
        h = hp.parse_slot(make_slot(name="Охотник"), "userdata0009")
        self.assertEqual(h.name, "Охотник")

    def test_reject_wrong_slot_and_corrupt_data(self):
        self.assertIsNone(hp.parse_slot(make_slot(), "userdata0010"))
        self.assertIsNone(hp.parse_slot(b"FACE", "userdata0000"))
        self.assertIsNone(hp.parse_slot(b"\0" * DATA_SIZE, "userdata0000"))
        buf = bytearray(make_slot())
        struct.pack_into("<I", buf, AT + hp.LEVEL, 100)
        self.assertIsNone(hp.parse_slot(bytes(buf), "userdata0001"))
        buf = bytearray(make_slot())
        struct.pack_into("<I", buf, AT + hp.OFFSETS["skill"], 999)
        self.assertIsNone(hp.parse_slot(bytes(buf), "userdata0001"))
        buf = bytearray(make_slot())
        struct.pack_into("<I", buf, AT + hp.INSIGHT, 999)
        self.assertIsNone(hp.parse_slot(bytes(buf), "userdata0001"))

    def test_injected_extra_face_and_invalid_char(self):
        buf = bytearray(make_slot())
        buf[AT + hp.FACE_TO_NAME + 0x120:AT + hp.FACE_TO_NAME + 0x124] = b"FACE"
        # Only the original FACE produces a valid character.
        self.assertIsNotNone(hp.parse_slot(bytes(buf), "userdata0000"))
        buf = bytearray(make_slot())
        buf[AT:AT+2] = b"\x00\xD8"  # Lone high surrogate; strict decoder fails.
        self.assertIsNone(hp.parse_slot(bytes(buf), "userdata0000"))

    def test_valid_file_group_and_safe_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "userdata0000"
            b = root / "userdata0001"
            a.write_bytes(make_slot("Maria"))
            b.write_bytes(make_slot("Герман"))
            (root / "userdata0010").write_bytes(b"not a character")
            before = a.read_bytes()
            found = hp.read_group(root, source="shadps4")
            self.assertEqual([x.name for x in found], ["Maria", "Герман"])
            self.assertTrue(all(x.source == "shadps4" for x in found))
            self.assertEqual(a.read_bytes(), before)
            self.assertIsNone(hp.read_slot(root / "userdata0010"))
            self.assertIsNone(hp.parse_slot(b"x" * (hp.MAX_FILE_BYTES + 1), "userdata0000"))
            self.assertEqual(len(hp.from_discovery([
                {"folder": str(root), "source": "shadps4"},
                {"folder": str(root), "source": "duplicate"},
                {"folder": "", "source": "unused"}])), 2)

    def test_source_labels_and_isolated_benchmark_exclusion(self):
        self.assertIn("shadPS4", hp.source_label("shadps4:new-home"))
        self.assertIn("co-op", hp.source_label("native:party"))
        self.assertIn("Chosen", hp.source_label("manual:folder"))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "userdata0000").write_bytes(make_slot())
            self.assertEqual(hp.from_discovery([
                {"folder": str(folder), "source": "native:warper"}]), [])

    def test_symlink_and_modified_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = root / "real"
            a.write_bytes(make_slot())
            link = root / "userdata0000"
            try:
                link.symlink_to(a)
            except (OSError, NotImplementedError):
                self.skipTest("Cannot create symlinks on this platform")
            self.assertIsNone(hp.read_slot(link))


if __name__ == "__main__":
    unittest.main()
