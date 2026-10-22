"""User-archive mod integration: offline, synthetic data, no copyrighted game assets."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from scripts import community_mods as cm


class CommunityModTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self._old_known = dict(cm.KNOWN)
        self.addCleanup(lambda: cm.KNOWN.clear() or cm.KNOWN.update(self._old_known))

    def make_zip(self, kind):
        entries = {}
        if kind == "jump":
            for choice in ("Jump only","Enhanced"):
                entries[f"Jump on L3 - Classic/{choice}/dvdroot_ps4/action/script/c0000.hks"] = choice.encode()
            entries["Jump on L3 - Classic/Backup/dvdroot_ps4/action/script/c0000.hks"] = b"NOT_FOR_INSTALL"
        if kind == "doll":
            entries.update({
                f"mods/DollRebirth/dvdroot_ps4/msg/lang{i}/menu.msgbnd.dcx": str(i).encode()
                for i in range(22)
            })
            entries["mods/DollRebirth/dvdroot_ps4/script/talk/m21_00_00_00.talkesdbnd.dcx"] = b"talk"
            entries["patches/DollRebirth.xml"] = b"<Patch/>"
        if kind == "moal":
            entries.update({
                f"MOAL/dvdroot_ps4/event/m{i:02d}_00_00_00.emevd.dcx": b"event"
                for i in range(15)
            })
            entries.update({
                f"MOAL/dvdroot_ps4/script/talk/m{i:02d}_00_00_00.talkesdbnd.dcx": b"talk"
                for i in range(16)
            })
        archive = self.root / (kind + ".zip")
        with zipfile.ZipFile(archive,"w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in entries.items():
                z.writestr(name, data)
        cm.KNOWN[hashlib.sha256(archive.read_bytes()).hexdigest()] = (kind,kind)
        return archive

    def test_jump_installer_does_not_touch_game_or_backup(self):
        archive = self.make_zip("jump")
        plan = cm.inspect([archive],self.data)
        self.assertEqual(plan.summary()["files"],1)
        self.assertFalse((self.data / "mods").exists())
        result = cm.install(plan,self.data)
        path = self.data / "mods/JumpOnL3Classic/dvdroot_ps4/action/script/c0000.hks"
        self.assertEqual(path.read_bytes(),b"Jump only")
        self.assertTrue(result["original_game_untouched"])
        self.assertFalse((self.data / "mods/JumpOnL3Classic/Backup").exists())
        with self.assertRaisesRegex(ValueError,"overwrite"):
            cm.inspect([archive],self.data)

    def test_jump_enhanced_is_explicit_choice(self):
        archive = self.make_zip("jump")
        plan = cm.inspect([archive],self.data,jump_variant="enhanced")
        cm.install(plan,self.data)
        self.assertEqual(
            (self.data / "mods/JumpOnL3Classic/dvdroot_ps4/action/script/c0000.hks").read_bytes(),
            b"Enhanced")

    def test_moal_requires_doll_and_patch(self):
        lamp = self.make_zip("moal")
        with self.assertRaisesRegex(ValueError,"requires DollRebirth"):
            cm.inspect([lamp],self.data)
        doll = self.make_zip("doll")
        plan = cm.inspect([lamp,doll],self.data)
        self.assertEqual(len(plan.files),55)
        cm.install(plan,self.data)
        self.assertTrue((self.data / "patches/DollRebirth.xml").is_file())
        self.assertTrue((self.data / "mods/MOAL/dvdroot_ps4/event/m00_00_00_00.emevd.dcx").is_file())
        self.assertTrue((self.data / "mods/DollRebirth/dvdroot_ps4/script/talk/m21_00_00_00.talkesdbnd.dcx").is_file())

    def test_solo_only_gameplay_mods_are_skipped_in_multiplayer(self):
        from scripts import mods
        self.assertTrue(mods.allowed_community_mod("MOAL", False))
        self.assertTrue(mods.allowed_community_mod("DollRebirth", False))
        self.assertFalse(mods.allowed_community_mod("MOAL", True))
        self.assertFalse(mods.allowed_community_mod("DollRebirth", True))
        self.assertTrue(mods.allowed_community_mod("JumpOnL3Classic", True))

    def test_manage_individual_mods_keeps_order_and_dependencies(self):
        doll = self.make_zip("doll")
        lamp = self.make_zip("moal")
        cm.install(cm.inspect([doll,lamp],self.data),self.data)
        (self.data/"mods.json").write_text(json.dumps(
            {"order":["DollRebirth","MOAL"],"disabled":[],"custom":"preserve"}))
        self.assertEqual(
            dict(cm.installed_mods(self.data)),
            {"DollRebirth":True,"MOAL":True})
        with self.assertRaisesRegex(ValueError,"DollRebirth enabled"):
            cm.save_mod_selection(self.data,["MOAL"])
        changed = cm.save_mod_selection(self.data,["DollRebirth"])
        self.assertIn("MOAL",changed["disabled"])
        config = json.loads((self.data/"mods.json").read_text())
        self.assertEqual(config["order"],["DollRebirth","MOAL"])
        self.assertEqual(config["custom"],"preserve")
        self.assertEqual(dict(cm.installed_mods(self.data))["MOAL"],False)
        cm.save_mod_selection(self.data,["DollRebirth","MOAL"])
        self.assertTrue(dict(cm.installed_mods(self.data))["MOAL"])

    def test_manage_doll_requires_active_code_patch(self):
        doll = self.make_zip("doll")
        cm.install(cm.inspect([doll],self.data),self.data)
        (self.data/"patches.json").write_text(json.dumps({
            "disabled":["DollRebirth.xml/Doll Rebirth (respec)"]}))
        with self.assertRaisesRegex(ValueError,"Enable the Doll Rebirth XML patch"):
            cm.save_mod_selection(self.data,["DollRebirth"])

    def test_refuse_conflicting_lamp_features(self):
        lamp, doll = self.make_zip("moal"),self.make_zip("doll")
        (self.data/"bbport.ini").write_text("pc_enhanced_lamps=1\n")
        with self.assertRaisesRegex(ValueError,"MOAL conflicts"):
            cm.inspect([lamp,doll],self.data)

    def test_refuse_enabled_external_script_conflict(self):
        jump = self.make_zip("jump")
        clash = self.data/"mods/SomeOtherMod/dvdroot_ps4/action/script/c0000.hks"
        clash.parent.mkdir(parents=True)
        clash.write_bytes(b"different gameplay")
        with self.assertRaisesRegex(ValueError,"Gameplay file conflict"):
            cm.inspect([jump],self.data)

    def test_refuse_disabled_doll_dependency(self):
        lamp,doll = self.make_zip("moal"),self.make_zip("doll")
        (self.data/"mods.json").write_text(json.dumps({"disabled":["DollRebirth"]}))
        with self.assertRaisesRegex(ValueError,"disabled"):
            cm.inspect([lamp,doll],self.data)

    def test_refuse_disabled_xml_dependency(self):
        lamp,doll = self.make_zip("moal"),self.make_zip("doll")
        (self.data/"patches.json").write_text(json.dumps({
            "disabled":["DollRebirth.xml/Doll Rebirth (respec)"]}))
        with self.assertRaisesRegex(ValueError,"disabled"):
            cm.inspect([lamp,doll],self.data)

    def test_refuse_changed_file_on_install(self):
        jump=self.make_zip("jump")
        plan=cm.inspect([jump],self.data)
        with zipfile.ZipFile(jump,"w") as z:
            z.writestr("Jump on L3 - Classic/Jump only/dvdroot_ps4/action/script/c0000.hks",b"changed")
        with self.assertRaisesRegex(ValueError,"changed"):
            cm.install(plan,self.data)
        self.assertFalse((self.data/"mods/JumpOnL3Classic").exists())

    def test_deny_unknown_and_duplicate_archive(self):
        jump=self.make_zip("jump")
        with self.assertRaisesRegex(ValueError,"one archive"):
            cm.inspect([jump,jump],self.data)
        cm.KNOWN.clear()
        with self.assertRaisesRegex(ValueError,"Unknown mod archive"):
            cm.inspect([jump],self.data)

    def test_reject_symlink_and_traversal_even_for_mock_signed_zip(self):
        for evil in ("../../savedata/user.sav","mods\\danger"):
            with self.subTest(evil=evil):
                archive=self.root/("evil"+str(abs(hash(evil)))+".zip")
                with zipfile.ZipFile(archive,"w") as z:
                    z.writestr(evil,b"bad")
                cm.KNOWN[hashlib.sha256(archive.read_bytes()).hexdigest()]=("jump","jump")
                # zipfile.ZipInfo normalizes backslashes to slashes on Windows,
                # where the resulting entry is still rejected as an alien layout.
                with self.assertRaisesRegex(ValueError,"Unsafe|unexpected mod file set"):
                    cm.inspect([archive],self.data)


if __name__ == "__main__":
    unittest.main()
