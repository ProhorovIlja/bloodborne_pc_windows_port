"""Realistic, synthetic Bloodborne install/save discovery; no private game files."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import struct
import unittest
from scripts import install_discovery as discovery


def fake_sfo(title_id, version):
    """Minimal correctly structured PSF like sce_sys/param.sfo."""
    items = (("TITLE_ID", title_id), ("APP_VER", version), ("TITLE", "Bloodborne"))
    keys = bytearray()
    values = bytearray()
    index = bytearray()
    for k, v in items:
        k_offset = len(keys)
        keys += k.encode() + b"\0"
        v_offset = len(values)
        value = v.encode() + b"\0"
        values += value
        index += struct.pack("<HHIII", k_offset, 0x204, len(value), len(value), v_offset)
    return (struct.pack("<4sIIII", b"\0PSF", 0x101,
                        20 + len(index), 20 + len(index) + len(keys), len(items))
            + index + keys + values)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.launcher = self.base / "Seamless Hunt PC"
        self.launcher.mkdir()

    def add_game(self, root, serial, version="01.09", sfo=True):
        root.mkdir(parents=True, exist_ok=True)
        (root / "eboot.bin").write_bytes(b"\x7fELF"+bytes(80))
        if sfo:
            (root/"sce_sys").mkdir(exist_ok=True)
            (root/"sce_sys/param.sfo").write_bytes(fake_sfo(serial, version))
        return root

    def add_save(self, path):
        path.mkdir(parents=True, exist_ok=True)
        (path/"userdata0000").write_bytes(b"user-save-private-data")

    def test_autofind_regional_games_and_report_older_patch(self):
        a = self.add_game(self.base/"Games"/"Bloodborne"/"CUSA00207", "CUSA00207")
        b = self.add_game(self.base/"games"/"CUSA03173", "CUSA03173", "01.08")
        fake = self.add_game(self.base/"Games"/"CUSA04321", "CUSA04321")
        result = discovery.scan(self.launcher, [self.base/"Games", self.base/"games"])
        paths = {x["folder"]: x for x in result["games"]}
        self.assertEqual(paths[str(a)]["status"], "candidate_109")
        self.assertEqual(paths[str(b)]["status"], "unsupported_patch")
        self.assertNotIn(str(fake), paths)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["all_patch_versions_supported"])
        self.assertTrue((a/"eboot.bin").is_file())

    def test_sfo_missing_is_uncertain_not_a_verified_game(self):
        found = self.add_game(self.base/"CUSA00900", "CUSA00900", sfo=False)
        x = discovery.scan(self.launcher,[self.base])
        self.assertEqual(x["games"][0]["folder"],str(found))
        self.assertEqual(x["games"][0]["status"],"unverified")
        self.assertEqual(x["games"][0]["title_id"],"CUSA00900")

    def test_does_not_confuse_random_eboot_with_bloodborne(self):
        self.add_game(self.base/"Games"/"Wrong", "CUSA04222")
        out = discovery.scan(self.launcher,[self.base/"Games"])
        self.assertFalse(out["games"])

    def test_shadps4_modern_and_classic_saves_plus_party(self):
        new = self.base/"shadPS4"/"home"/"1000"/"savedata"/"CUSA00207"/"SPRJ0005"
        old = self.base/"shadPS4"/"user"/"savedata"/"1"/"CUSA03173"/"SPRJ0005"
        party = self.launcher/"user"/"savedata_party"/"1"/"CUSA00900"/"SPRJ0005"
        for p in (new, old, party):
            self.add_save(p)
        env = {"APPDATA":str(self.base), "LOCALAPPDATA":str(self.base/"nope")}
        # Extra root points at portable shadPS4 layout, installed launcher at own root.
        with patch.dict(os.environ, env):
            s = discovery.find_saves(self.launcher, extra_roots=[self.base/"shadPS4"])
        found = {v.folder: v for v in s}
        for p in (new, old, party):
            self.assertIn(str(p),found)
            self.assertIn("CUSA",found[str(p)].title_id)
        self.assertTrue(all("Detected only" in item.compatibility for item in s))
        self.assertEqual((new/"userdata0000").read_bytes(),b"user-save-private-data")

    def test_found_game_mod_patch_and_cheat_dirs_are_read_only(self):
        game = self.add_game(self.base/"Games"/"CUSA03173", "CUSA03173")
        for folder,filename in [(game/"mods","example.dcx"),
                                (self.launcher/"patches","Bloodborne.xml"),
                                (self.launcher/"cheats","example.json")]:
            folder.mkdir(parents=True)
            (folder/filename).write_text("unchanged")
        result = discovery.scan(self.launcher,[self.base/"Games"])
        kinds = {e["kind"] for e in result["extras"]}
        self.assertEqual(kinds,{"mods","patches","cheats"})
        self.assertFalse(result["saves_migrated"])

    def test_symlinked_game_is_not_followed(self):
        real = self.add_game(self.base/"Outside"/"CUSA03173","CUSA03173")
        link = self.base/"Games"/"CUSA03173"
        link.parent.mkdir()
        try:
            link.symlink_to(real, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        found = discovery.find_games(self.launcher,[link.parent])
        self.assertFalse(found)


if __name__ == "__main__":
    unittest.main()
