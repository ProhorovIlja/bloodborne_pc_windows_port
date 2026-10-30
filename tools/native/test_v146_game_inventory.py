"""Privacy, read-only and deterministic tests for the native dump inventory."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import StringIO
from pathlib import Path
import json
import os
import tempfile
import unittest

p = Path(__file__).with_name("v146_game_inventory.py")
spec = importlib.util.spec_from_file_location("v146_game_inventory", p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NativeInventoryV146Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "CUSA03173"
        (self.root / "sce_sys").mkdir(parents=True)
        (self.root / "sce_module").mkdir()
        (self.root / "dvdroot_ps4" / "shader").mkdir(parents=True)
        (self.root / "eboot.bin").write_bytes(b"FAKE TEST ONLY")
        (self.root / "sce_sys" / "param.sfo").write_bytes(b"not a real SFO")
        (self.root / "sce_module" / "libc.prx").write_bytes(b"no PS4 code")
        (self.root / "dvdroot_ps4" / "shader" / "sample.dcx").write_bytes(b"opaque")
        (self.root / "dvdroot_ps4" / "PRIVATE_HUNTER_BUILD.param").write_bytes(b"SECRET_CONTENT")
    def test_default_reports_no_paths_no_bytes_no_private_content(self):
        result=mod.inventory(self.root)
        raw=json.dumps(result)
        self.assertEqual(result["schema"],"SHYT_NATIVE_ASSET_INVENTORY_V1")
        self.assertEqual(result["files"],5)
        self.assertEqual(result["extensions"][0]["extension"],".bin")
        self.assertTrue(all(result["required"].values()))
        self.assertTrue(result["content_dirs"]["dvdroot_ps4/shader"])
        self.assertNotIn("relative_file_entries", result)
        self.assertNotIn("PRIVATE_HUNTER_BUILD",raw)
        self.assertNotIn("SECRET_CONTENT",raw)
        self.assertNotIn(str(self.root),raw)
        self.assertNotIn("CUSA03173",raw)
        self.assertFalse(result["privacy"]["game_bytes_uploaded"])
        self.assertFalse(result["privacy"]["relative_paths_included"])
    def test_opt_in_paths_only_remain_relative_and_sorted(self):
        result=mod.inventory(self.root,include_paths=True)
        files=[e["path"] for e in result["relative_file_entries"]]
        self.assertEqual(len(files),5)
        self.assertIn("dvdroot_ps4/PRIVATE_HUNTER_BUILD.param",files)
        self.assertNotIn("SECRET_CONTENT",json.dumps(result))
        self.assertTrue(all(not x.startswith("/") and ":" not in x for x in files))
        self.assertEqual(result["bytes"],sum(x["bytes"] for x in result["relative_file_entries"]))
    def test_regular_game_files_never_modified_even_when_writing_report(self):
        original=(self.root/"eboot.bin").read_bytes()
        dest=Path(self.temp.name)/"native-metadata.json"
        output=StringIO()
        with redirect_stdout(output):
            self.assertEqual(mod.main([str(self.root),"--output",str(dest)]),0)
        parsed=json.loads(dest.read_text(encoding="utf-8"))
        self.assertEqual(parsed["files"],5)
        self.assertEqual((self.root/"eboot.bin").read_bytes(),original)
        self.assertNotIn(str(self.root),dest.read_text())
    def test_reject_output_inside_game_folder(self):
        target=self.root/"do-not-write.json"
        with redirect_stderr(StringIO()):
            result=mod.main([str(self.root),"--output",str(target)])
        self.assertEqual(result,2)
        self.assertFalse(target.exists())
    def test_missing_executable_and_invalid_image_are_fail_closed(self):
        (self.root/"eboot.bin").unlink()
        with self.assertRaisesRegex(mod.InventoryError,"eboot.bin"):
            mod.inventory(self.root)
        (self.root/"eboot.bin").write_bytes(b"FAKE")
        with self.assertRaisesRegex(mod.InventoryError,"native game metadata"):
            mod.inventory(self.root,verify_image=True)
    def test_skip_symlinks_and_notice_case_collisions(self):
        (self.root/"dvdroot_ps4"/"shader"/"Sample.dcx").write_bytes(b"B")
        result=mod.inventory(self.root)
        self.assertEqual(result["case_insensitive_path_collisions"],1)
        other=Path(self.temp.name)/"PRIVATE_KEY.txt"
        other.write_text("DO_NOT_READ")
        link=self.root/"outside-link.txt"
        try:
            os.symlink(other,link)
        except (OSError,NotImplementedError):
            self.skipTest("symlink requires elevated Windows permission")
        result=mod.inventory(self.root,include_paths=True)
        self.assertEqual(result["symlinks_skipped"],1)
        self.assertEqual(result["files"],6)
        self.assertNotIn("outside-link.txt",[x["path"] for x in result["relative_file_entries"]])
        self.assertNotIn("DO_NOT_READ",json.dumps(result))
    def test_reject_accidental_drive_roots_and_limit(self):
        missing=Path(self.temp.name)
        with self.assertRaisesRegex(mod.InventoryError,"eboot.bin"):
            mod.inventory(missing)
        old=mod.MAX_FILES
        try:
            mod.MAX_FILES=3
            with self.assertRaisesRegex(mod.InventoryError,"bounded inventory"):
                mod.inventory(self.root)
        finally:
            mod.MAX_FILES=old


if __name__ == "__main__":
    unittest.main()
