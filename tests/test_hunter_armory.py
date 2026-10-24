"""Synthetic-only armory and game localization fixtures; no retail data included."""
import struct
import tempfile
import unittest
from pathlib import Path
import zlib

import paths  # noqa: F401
import hunter_armory as ar
import hunter_profiles as hp
from test_hunter_profiles import AT, make_slot


def bnd_and_dcx(weapon_id: int, label: str) -> bytes:
    """Create bounded minimal FMG/BND4/DFLT archives with one string."""
    fmg = bytearray(0x60 + len(label.encode("utf-16-le")) + 2)
    struct.pack_into("<I", fmg, 0x0C, 1)
    struct.pack_into("<Q", fmg, 0x18, 0x40)
    struct.pack_into("<iii", fmg, 0x28, 0, weapon_id, weapon_id)
    struct.pack_into("<q", fmg, 0x40, 0x60)
    fmg[0x60:] = label.encode("utf-16-le") + b"\0\0"

    bnd = bytearray(0x80 + len(fmg))
    bnd[:4] = b"BND4"
    struct.pack_into("<I", bnd, 0x0C, 1)
    struct.pack_into("<Q", bnd, 0x20, 0x24)
    struct.pack_into("<Q", bnd, 0x40 + 8, len(fmg))
    struct.pack_into("<I", bnd, 0x40 + 0x18, 0x80)
    struct.pack_into("<I", bnd, 0x40 + 0x1C, 11)
    bnd[0x80:] = fmg

    dcx = bytearray(0x4C)
    dcx[:4] = b"DCX\0"
    dcx[0x28:0x2C] = b"DFLT"
    return bytes(dcx) + zlib.compress(bytes(bnd))


class ArmoryTests(unittest.TestCase):
    def test_owned_not_equipped_and_upgrade_dedup(self):
        data = bytearray(make_slot())
        base = AT + ar.INVENTORY_OFFSET
        # Same trick weapon variant twice at +3 and +8; keep the higher upgrade.
        for pos, ident in enumerate((2000300, 2000800, 6000200, 2100500)):
            struct.pack_into("<I", data, base + pos * ar.ENTRY_SIZE + 8, ident)
        # Unrecognized id and invalid partial identifier skipped.
        struct.pack_into("<I", data, base + 5 * ar.ENTRY_SIZE + 8, 2000801)
        # Armor mask should skip even an otherwise valid weapon identifier.
        armor = base + 6 * ar.ENTRY_SIZE
        struct.pack_into("<I", data, armor + 8, 2000100)
        data[armor + 11] = 0x10
        h = hp.parse_slot(bytes(data), "userdata0000")
        self.assertIsNotNone(h)
        self.assertEqual(h.owned_weapon_ids, (2000800, 6000200))
        self.assertNotIn("equipped_weapon", h.public())
        self.assertIn("Right-hand", ar.weapon_description(2000800))
        self.assertIn("Left-hand", ar.weapon_description(6000200))
        self.assertIn("+8", ar.weapon_description(2000800))
        self.assertEqual(ar.weapon_description(2000800, {2000000: "Test Weapon"}),
                         "Test Weapon +8 · Right-hand")

    def test_empty_and_short_inventory(self):
        self.assertEqual(ar.owned_weapon_ids(make_slot(), AT), ())
        self.assertEqual(ar.owned_weapon_ids(b"xyz", AT), ())

    def test_synthetic_localized_weapon_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            game_dir = Path(tmp)
            loc = game_dir / "dvdroot_ps4" / "msg" / "engus"
            loc.mkdir(parents=True)
            archive = loc / "item.msgbnd.dcx"
            archive.write_bytes(bnd_and_dcx(2000000, "Test Saw"))
            names = ar.game_weapon_names(str(game_dir), "8")  # Russian missing -> English
            self.assertEqual(names[2000000], "Test Saw")
            self.assertEqual(ar.weapon_description(2000600, names), "Test Saw +6 · Right-hand")
            self.assertEqual(ar.weapon_description(2000000, {2000000: "Test Saw"}),
                             "Test Saw · Right-hand")
            self.assertEqual(ar.weapon_description(2000000, {2000000: "Test Saw"}).count("Test Saw"), 1)

    def test_malformed_message_data_rejected(self):
        data = bnd_and_dcx(2000000, "Test")
        with self.assertRaises(ValueError):
            ar.decompress_game_text(b"x" * 128)
        with self.assertRaises(ValueError):
            ar.decompress_game_text(data[:-3])
        with self.assertRaises(ValueError):
            ar.item_archive_member(b"bad")
        with self.assertRaises(ValueError):
            ar.fmg_weapon_names(b"\0" * 20)
        archive = bytearray(ar.decompress_game_text(data))
        struct.pack_into("<I", archive, 0x40 + 0x18, len(archive) + 5)
        with self.assertRaises(ValueError):
            ar.item_archive_member(bytes(archive))
        fmg = bytearray(0x50)
        struct.pack_into("<I", fmg, 0x0C, 1000000)
        with self.assertRaises(ValueError):
            ar.fmg_weapon_names(bytes(fmg))
        self.assertEqual(ar.weapon_description(99999999), "Unknown weapon")


if __name__ == "__main__":
    unittest.main()
