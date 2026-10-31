"""V176: synthetic private game/mod fixtures only, never uploaded to Actions."""
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
from io import StringIO
import json
import os
import tempfile
import unittest

p=Path(__file__).with_name("v176_mod_overlay_audit.py")
spec=importlib.util.spec_from_file_location("yt176_mod_audit",p)
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class NativeModPreflightV176(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"MODS"
        self.root.mkdir()
        self.jump=self.root/"Jump on O+L3 - Jump Attack on X+R1"
        self.moal=self.root/"MOAL"
        (self.jump/"action").mkdir(parents=True)
        (self.moal/"script"/"talk").mkdir(parents=True)
        (self.jump/"action"/"c0000.behbnd.dcx").write_bytes(b"PRIVATE_GAME_BYTES")
        (self.moal/"script"/"talk"/"m21.talkesdbnd.dcx").write_bytes(b"PRIVATE_MOD_BYTES")
        (self.moal/"script"/"talk"/"m21.talkesdbnd.dcx.bak").write_bytes(b"BACKUP")

    def test_actual_named_mod_layout_but_private_report(self):
        report=a.audit(self.root)
        data=json.dumps(report)
        self.assertEqual(report["schema"],a.SCHEMA)
        self.assertEqual(report["mod_directories"],2)
        self.assertEqual(report["ready_for_manual_review_mods"],2)
        self.assertEqual(report["conflicting_relative_paths"],0)
        self.assertEqual(sum(m["backups_ignored"] for m in report["mods"]),1)
        for secret in ("MOAL","PRIVATE_GAME_BYTES","PRIVATE_MOD_BYTES",
                       str(self.root),"Jump on"):
            self.assertNotIn(secret,data)

    def test_conflict_and_existing_overlay_match_case_insensitively(self):
        (self.moal/"action").mkdir()
        (self.moal/"action"/"C0000.BEHBND.DCX").write_bytes(b"MOD2")
        overlay=Path(self.temp.name)/"CUSA03173-mods"/"dvdroot_ps4"/"action"
        overlay.mkdir(parents=True)
        (overlay/"c0000.behbnd.dcx").write_bytes(b"EXISTING")
        report=a.audit(self.root,existing_overlay=overlay.parents[1],
                       include_paths=True)
        self.assertEqual(report["conflicting_relative_paths"],1)
        self.assertEqual(report["existing_overlay_path_overrides"],1)
        self.assertEqual(report["collisions"][0]["relative_path"],"action/c0000.behbnd.dcx")
        self.assertEqual(len(report["collisions"][0]["mods"]),2)
        self.assertNotIn(str(self.root),json.dumps(report))

    def test_nested_wrong_structure_and_executable_are_not_installed(self):
        wrong=self.root/"Nested"
        (wrong/"dvdroot_ps4"/"map").mkdir(parents=True)
        (wrong/"dvdroot_ps4"/"map"/"m01.dcx").write_bytes(b"test")
        unsafe=self.root/"Unsafe"
        (unsafe/"script").mkdir(parents=True)
        (unsafe/"script"/"patcher.exe").write_bytes(b"PE")
        report=a.audit(self.root)
        self.assertEqual(report["manual_review_mods"],1)
        self.assertEqual(report["blocked_mods"],1)
        self.assertTrue((unsafe/"script"/"patcher.exe").is_file())

    def test_symlink_not_followed_or_read(self):
        foreign=Path(self.temp.name)/"external"
        foreign.mkdir()
        (foreign/"secret").write_bytes(b"SENSITIVE")
        try:
            os.symlink(foreign,self.jump/"map",target_is_directory=True)
        except OSError:
            self.skipTest("symlink not supported")
        report=a.audit(self.root,include_paths=True)
        self.assertEqual(report["blocked_mods"],1)
        self.assertNotIn("SENSITIVE",json.dumps(report))
        self.assertNotIn("secret",json.dumps(report))

    def test_archive_ignored_local_output_refuses_mutation(self):
        (self.root/"MOAL.zip").write_bytes(b"ARCHIVE_UNINSPECTED")
        with redirect_stderr(StringIO()):
            self.assertEqual(a.main([str(self.root),"--output",
                                     str(self.root/"audit.json")]),2)
        self.assertFalse((self.root/"audit.json").exists())
        result=Path(self.temp.name)/"report.json"
        self.assertEqual(a.main([str(self.root),"--output",str(result)]),0)
        self.assertEqual(json.loads(result.read_text())["archives_uninspected"],1)
        self.assertNotIn("ARCHIVE_UNINSPECTED",result.read_text())

    def test_private_paths_never_stream_to_console(self):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = a.main([str(self.root), "--include-paths"])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("requires explicit local --output", errors.getvalue())
        self.assertNotIn("MOAL", errors.getvalue())

    def test_stdout_budget_rejects_without_partial_report(self):
        old = a.MAX_STDOUT_JSON_BYTES
        try:
            a.MAX_STDOUT_JSON_BYTES = 100
            output, errors = StringIO(), StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                status = a.main([str(self.root)])
            self.assertEqual(status, 2)
            self.assertEqual(output.getvalue(), "")
            self.assertIn("safe output budget", errors.getvalue())
        finally:
            a.MAX_STDOUT_JSON_BYTES = old

    def test_explicit_local_path_report_is_allowed_and_bounded(self):
        dest = Path(self.temp.name) / "private-mod-report.json"
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(a.main([str(self.root), "--include-paths",
                                     "--output", str(dest)]), 0)
        self.assertEqual(output.getvalue(), "")
        report = json.loads(dest.read_text(encoding="utf-8"))
        self.assertTrue(report["privacy"]["relative_paths_opt_in"])
        self.assertEqual(report["mod_directories"], 2)
        self.assertNotIn("PRIVATE_MOD_BYTES", dest.read_text(encoding="utf-8"))
        old = a.MAX_REPORT_FILE_BYTES
        try:
            a.MAX_REPORT_FILE_BYTES = 100
            oversize = Path(self.temp.name) / "blocked-report.json"
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(a.main([str(self.root), "--output", str(oversize)]), 2)
            self.assertFalse(oversize.exists())
        finally:
            a.MAX_REPORT_FILE_BYTES = old

    def test_scan_limit_and_case_collision(self):
        (self.jump/"action"/"C0000.BEHBND.DCX").write_bytes(b"collision")
        report=a.audit(self.root)
        if os.name!="nt":
            self.assertEqual(report["blocked_mods"],1)
        old=a.MAX_FILES
        try:
            a.MAX_FILES=0
            with self.assertRaisesRegex(a.AuditError,"bound"):
                a.audit(self.root)
        finally:
            a.MAX_FILES=old


if __name__=="__main__":
    unittest.main()
