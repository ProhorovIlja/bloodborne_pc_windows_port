"""V154 synthetic DS3/BB reference inventory: no game bytes, no personal paths."""
import importlib.util
from pathlib import Path
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

p=Path(__file__).with_name("v154_ds3_reference_inventory.py")
spec=importlib.util.spec_from_file_location("v154_ds3_ref",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Ds3ReferenceV154Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"PRIVATE_DS3_INSTALL"/"Game"
        self.root.mkdir(parents=True)
        (self.root/"DarkSoulsIII.exe").write_bytes(b"SYNTHETIC_NO_EXECUTABLE_CONTENT")
        for name in ("Data0.bdt","Data1.bhd","Data1.bdt","Data5.bdt"):
            (self.root/name).write_bytes(b"SECRET_GAME_DATA")
        (self.root/"sound").mkdir()
        (self.root/"sound"/"private_audio.fsb").write_bytes(b"SOUND_SECRET")
        (self.root/"movie").mkdir()
        (self.root/"movie"/"private_movie.bik").write_bytes(b"MOVIE_SECRET")

    def test_anonymous_metadata_only_and_archive_pairs(self):
        report=m.inventory(self.root.parent)
        raw=json.dumps(report)
        self.assertEqual(report["schema"],"SHYT_DS3_PC_REFERENCE_V154")
        self.assertEqual(report["files"],7)
        self.assertTrue(report["known_archives"]["Data1"]["index_present"])
        self.assertFalse(report["known_archives"]["Data5"]["index_present"])
        self.assertTrue(report["known_dirs"]["sound"])
        self.assertFalse(report["privacy"]["game_contents_read"])
        self.assertFalse(report["engine_compatibility_proven"])
        for secret in ("PRIVATE_DS3_INSTALL","private_audio","private_movie","SECRET","SYNTHETIC",str(self.root)):
            self.assertNotIn(secret,raw)
        self.assertEqual(sum(x["files"] for x in report["extensions"]),7)

    def test_bb_v146_report_comparison_never_repeats_sensitive_metadata(self):
        p=Path(self.temp.name)/"bb-v146.json"
        p.write_text(json.dumps({
            "schema":m.BB_SCHEMA,
            "privacy":{"relative_paths_included":False},
            "extensions":[{"extension":".msb","files":12,"bytes":180},
                          {"extension":".dcx","files":4,"bytes":900}],
            "untrusted_raw_meta":"SECRET_PRIVATE_BB_PATH"
        }))
        report=m.inventory(self.root,p)
        rows={x["family"]:x for x in report["bloodborne_comparison"]["family_visible_file_counts"]}
        self.assertEqual(rows["world_events"]["bloodborne_visible_files"],12)
        self.assertEqual(rows["compression"]["bloodborne_visible_files"],4)
        self.assertNotIn("SECRET_PRIVATE_BB_PATH",json.dumps(report))
        p.write_text(json.dumps({"schema":m.BB_SCHEMA,"privacy":{"relative_paths_included":True},
                                 "extensions":[]}))
        with self.assertRaises(m.InventoryError):
            m.inventory(self.root,p)

    def test_no_mutations_and_no_overwrite_even_when_saving_report(self):
        original=(self.root/"DarkSoulsIII.exe").read_bytes()
        out=Path(self.temp.name)/"anon.json"
        with redirect_stdout(StringIO()):
            self.assertEqual(m.main([str(self.root),"--output",str(out)]),0)
        self.assertEqual((self.root/"DarkSoulsIII.exe").read_bytes(),original)
        self.assertFalse(json.loads(out.read_text())["privacy"]["game_bytes_uploaded"])
        with redirect_stderr(StringIO()):
            self.assertEqual(m.main([str(self.root),"--output",str(out)]),2)
            self.assertEqual(m.main([str(self.root),"--output",str(self.root/"bad.json")]),2)
        self.assertFalse((self.root/"bad.json").exists())

    def test_reject_bad_folder_symlink_and_file_limit(self):
        untrusted=Path(self.temp.name)/"not-game"
        untrusted.mkdir()
        with self.assertRaises(m.InventoryError):
            m.game_root(untrusted)
        target=Path(self.temp.name)/"private_secret.exe"
        target.write_bytes(b"DO_NOT_READ")
        link=self.root/"other.exe"
        try:
            link.symlink_to(target)
        except (OSError,NotImplementedError):
            self.skipTest("Windows symlink privilege required")
        self.assertEqual(m.inventory(self.root)["symlinks_skipped"],1)
        original=m.MAX_FILES
        try:
            m.MAX_FILES=2
            with self.assertRaisesRegex(m.InventoryError,"count exceeded"):
                m.inventory(self.root)
        finally:
            m.MAX_FILES=original

if __name__=="__main__":
    unittest.main()
