"""scripts/party_saves.py: the launcher's copy of the single-player save into the party save folder."""
import paths  # noqa: F401  (puts scripts/ on sys.path)
import tempfile
from unittest import mock
import unittest
from pathlib import Path

import party_saves as ps

SAVE = "1/CUSA03173/SPRJ0005"


def write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def snapshot(folder: Path) -> dict:
    return {p.relative_to(folder).as_posix(): (p.stat().st_mtime_ns, p.read_bytes())
            for p in folder.rglob("*") if p.is_file()}


class PartySaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.user = Path(self.tmp.name)
        write(self.user / ps.SOLO / SAVE / "userdata0000", b"A" * 4096)
        write(self.user / ps.SOLO / SAVE / "userdata0010", b"B" * 1024)
        write(self.user / ps.SOLO / (SAVE + ".sce_sys") / "param.bin", b"P" * 1328)
        write(self.user / ps.SOLO / SAVE / "userdata0000.3.bbtmp", b"partial")

    def tearDown(self):
        self.tmp.cleanup()

    def test_offer_only_when_party_folder_is_empty(self):
        self.assertTrue(ps.should_offer_copy(self.user))
        (self.user / ps.PARTY).mkdir()
        self.assertTrue(ps.should_offer_copy(self.user))  # an empty folder is no save
        write(self.user / ps.PARTY / SAVE / "userdata0000", b"C")
        self.assertFalse(ps.should_offer_copy(self.user))

    def test_no_offer_without_single_player_save(self):
        empty = self.user / "other"
        empty.mkdir()
        self.assertFalse(ps.should_offer_copy(empty))
        with self.assertRaises(FileNotFoundError):
            ps.copy_solo_to_party(empty)

    def test_copy_reads_solo_only(self):
        before = snapshot(self.user / ps.SOLO)
        self.assertIsNone(ps.copy_solo_to_party(self.user))
        self.assertEqual(snapshot(self.user / ps.SOLO), before)
        party = self.user / ps.PARTY
        self.assertEqual((party / SAVE / "userdata0000").read_bytes(), b"A" * 4096)
        self.assertTrue((party / (SAVE + ".sce_sys") / "param.bin").is_file())
        self.assertFalse((party / SAVE / "userdata0000.3.bbtmp").exists())
        self.assertFalse((self.user / (ps.PARTY + ".copying")).exists())

    def test_existing_party_save_is_kept_or_backed_up(self):
        write(self.user / ps.PARTY / SAVE / "userdata0000", b"party progress")
        with self.assertRaises(FileExistsError):
            ps.copy_solo_to_party(self.user)
        self.assertEqual((self.user / ps.PARTY / SAVE / "userdata0000").read_bytes(), b"party progress")
        backup = ps.copy_solo_to_party(self.user, replace=True)
        self.assertEqual((backup / SAVE / "userdata0000").read_bytes(), b"party progress")
        self.assertEqual(backup.parent, self.user / ps.BACKUPS / ps.PARTY)
        self.assertEqual((self.user / ps.PARTY / SAVE / "userdata0000").read_bytes(), b"A" * 4096)


class PartySaveRecoveryTests(PartySaveTests):
    """Run only on TemporaryDirectory user data, never real profile saves."""

    def _old_party(self):
        old = self.user / ps.PARTY / SAVE / "userdata0000"
        write(old, b"older party with priceless progress")
        return old

    def test_older_backups_survive_multiple_replacements(self):
        old = self._old_party()
        original = old.read_bytes()
        first = ps.copy_solo_to_party(self.user, replace=True)
        self.assertEqual((first / SAVE / "userdata0000").read_bytes(), original)
        self.assertEqual(old.read_bytes(), b"A" * 4096)
        second = ps.copy_solo_to_party(self.user, replace=True)
        self.assertNotEqual(first, second)
        self.assertEqual((first / SAVE / "userdata0000").read_bytes(), original)
        self.assertEqual((second / SAVE / "userdata0000").read_bytes(), b"A" * 4096)
        self.assertEqual(old.read_bytes(), b"A" * 4096)

    def test_staging_rename_fail_rolls_back_old_party(self):
        original = self._old_party().read_bytes()
        rename = Path.rename
        def fail_new_staging(source, dest):
            if source.name.startswith("." + ps.PARTY + ".copying-") and Path(dest).name == ps.PARTY:
                raise PermissionError("simulated antivirus lock during promotion")
            return rename(source, dest)
        with mock.patch.object(Path, "rename", fail_new_staging):
            with self.assertRaises(PermissionError):
                ps.copy_solo_to_party(self.user, replace=True)
        self.assertEqual((self.user / ps.PARTY / SAVE / "userdata0000").read_bytes(), original)
        self.assertEqual(list((self.user / ps.BACKUPS / ps.PARTY).glob("*.pending-replaced")), [])
        self.assertFalse((self.user / ps.LOCK).exists())

    def test_crash_between_moves_survives_in_pending_backup_and_recovers(self):
        original = self._old_party().read_bytes()
        rename = Path.rename
        def interrupt(source, dest):
            if source.name.startswith("." + ps.PARTY + ".copying-") and Path(dest).name == ps.PARTY:
                raise KeyboardInterrupt("simulated process crash")
            return rename(source, dest)
        with mock.patch.object(Path, "rename", interrupt):
            with self.assertRaises(KeyboardInterrupt):
                ps.copy_solo_to_party(self.user, replace=True)
        pending = list((self.user / ps.BACKUPS / ps.PARTY).glob("*.pending-replaced"))
        self.assertEqual(len(pending), 1)
        self.assertFalse((self.user / ps.PARTY).exists())
        self.assertEqual((pending[0] / SAVE / "userdata0000").read_bytes(), original)
        with self.assertRaisesRegex(RuntimeError, "interrupted party copy recovered"):
            ps.copy_solo_to_party(self.user, replace=True)
        self.assertEqual((self.user / ps.PARTY / SAVE / "userdata0000").read_bytes(), original)
        self.assertFalse(pending[0].exists())

    def test_failed_restore_leaves_only_good_backup_not_destroyed(self):
        original = self._old_party().read_bytes()
        rename = Path.rename
        def fail_promote_and_restore(source, dest):
            if Path(dest).name == ps.PARTY:
                raise PermissionError("blocked party save location")
            return rename(source, dest)
        with mock.patch.object(Path, "rename", fail_promote_and_restore):
            with self.assertRaises(PermissionError):
                ps.copy_solo_to_party(self.user, replace=True)
        pending = list((self.user / ps.BACKUPS / ps.PARTY).glob("*.pending-replaced"))
        self.assertEqual(len(pending), 1)
        self.assertEqual((pending[0] / SAVE / "userdata0000").read_bytes(), original)
        self.assertFalse((self.user / ps.PARTY).exists())
        with self.assertRaisesRegex(RuntimeError, "interrupted party copy recovered"):
            ps.copy_solo_to_party(self.user, replace=True)
        self.assertEqual((self.user / ps.PARTY / SAVE / "userdata0000").read_bytes(), original)

    def test_same_size_corruption_in_staging_is_detected(self):
        original = self._old_party().read_bytes()
        real = ps.shutil.copytree
        def corrupt(source, dest, *args, **kwargs):
            result = real(source, dest, *args, **kwargs)
            copied = Path(dest) / SAVE / "userdata0000"
            copied.write_bytes(b"X" * 4096)
            return result
        with mock.patch.object(ps.shutil, "copytree", side_effect=corrupt):
            with self.assertRaisesRegex(OSError, "changed during verification"):
                ps.copy_solo_to_party(self.user, replace=True)
        self.assertEqual((self.user / ps.PARTY / SAVE / "userdata0000").read_bytes(), original)

    def test_stale_lock_does_not_allow_overlapping_copy(self):
        self._old_party()
        lock = self.user / ps.LOCK
        lock.write_text("a second launcher is still working")
        with self.assertRaises(FileExistsError):
            ps.copy_solo_to_party(self.user, replace=True)
        self.assertTrue(lock.exists())

    def test_stale_pending_backup_not_deleted_when_active_exists(self):
        self._old_party()
        base = self.user / ps.BACKUPS / ps.PARTY
        base.mkdir(parents=True)
        pending = base / "prior.pending-replaced"
        write(pending / SAVE / "userdata0000", b"last run backup")
        old_copy = ps.copy_solo_to_party(self.user, replace=True)
        self.assertFalse(pending.exists())
        completed = base / "prior-replaced"
        self.assertEqual((completed / SAVE / "userdata0000").read_bytes(), b"last run backup")
        self.assertTrue((old_copy / SAVE / "userdata0000").is_file())

    def test_existing_empty_party_dir_still_accepts_first_copy(self):
        (self.user / ps.PARTY).mkdir()
        self.assertIsNone(ps.copy_solo_to_party(self.user))
        self.assertEqual((self.user / ps.PARTY / SAVE / "userdata0000").read_bytes(), b"A" * 4096)

    def test_symlink_source_and_party_are_rejected(self):
        outside = self.user / "other"
        outside.mkdir()
        link = self.user / ps.SOLO / "symlink"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation not permitted on runner")
        with self.assertRaises(OSError):
            ps.copy_solo_to_party(self.user)
        link.unlink()
        party = self.user / ps.PARTY
        party.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            ps.copy_solo_to_party(self.user, replace=True)


class LauncherEnvTests(unittest.TestCase):
    def test_party_env_save_policy(self):
        import importlib.util
        from paths import ROOT
        try:
            spec = importlib.util.spec_from_file_location("bb_launcher", ROOT / "launcher.py")
            launcher = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(launcher)
        except Exception as ex:  # no tkinter / display
            self.skipTest(f"launcher.py not importable here: {ex}")
        env = launcher.party_env({"party_mode": "host"})
        self.assertEqual(env["BB_PARTY_SAVE"], "separate")
        # The old shared choice is gone: a party session always plays from the party saves.
        env = launcher.party_env({"party_mode": "join", "party_separate_save": False})
        self.assertEqual(env["BB_PARTY_SAVE"], "separate")
        self.assertIsNone(launcher.party_env({"party_mode": ""})["BB_PARTY_SAVE"])
        self.assertEqual(launcher.party_saves_module().PARTY, "savedata_party")

    def test_party_env_rules_and_sync(self):
        import importlib.util
        from paths import ROOT
        try:
            spec = importlib.util.spec_from_file_location("bb_launcher", ROOT / "launcher.py")
            launcher = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(launcher)
        except Exception as ex:  # no tkinter / display
            self.skipTest(f"launcher.py not importable here: {ex}")
        # Defaults = the game's defaults (docs/party/DEBUG_SWITCHES.md, docs/PARTY.md)
        env = launcher.party_env({"party_mode": "host"})
        expected = {"BB_PARTY_START": "prologue_solo", "BB_SAVE_BACKUP_MINUTES": "10", "BB_SAVE_BACKUP_KEEP": "10",
                    "BB_PARTY_RESTART": "1"}
        for key, value in expected.items():
            self.assertEqual(env[key], value, key)
        # The party gameplay switches and the guest Insight live in bbport.ini (0.7.0): never set here
        for name in ("BB_PARTY_GUEST_INSIGHT", "BB_PARTY_GRANT_BELLS", "BB_PARTY_ITEMS", "BB_PARTY_STORY_MIRROR",
                     "BB_PARTY_HOST_LIMBO_REVIVE", "BB_PARTY_B2_HOST_REVIVE", "BB_PARTY_GUEST_REVIVE_INPLACE"):
            self.assertIn(name, env)
            self.assertIsNone(env[name], name)
        env = launcher.party_env({"party_mode": "join", "party_start": "immediate", "party_guest_insight": "0",
                                  "party_backup_minutes": "0", "party_backup_keep": "50",
                                  "party_progress_npc": False, "party_restart": False})
        self.assertEqual((env["BB_PARTY_START"], env["BB_PARTY_GUEST_INSIGHT"]), ("immediate", None))
        self.assertEqual((env["BB_SAVE_BACKUP_MINUTES"], env["BB_SAVE_BACKUP_KEEP"]), ("0", "50"))
        self.assertEqual((env["BB_PARTY_PROGRESS_NPC"], env["BB_PARTY_RESTART"]), (None, "0"))
        # Bad values fall back to the defaults
        env = launcher.party_env({"party_mode": "host", "party_start": "x", "party_backup_keep": "7"})
        self.assertEqual((env["BB_PARTY_START"], env["BB_SAVE_BACKUP_KEEP"]), ("prologue_solo", "10"))
        # Party off: every party variable is unset (run.bat sees none of them)
        off = launcher.party_env({"party_mode": "", "party_restart": False})
        self.assertTrue(all(v is None for v in off.values()))
        self.assertIn("BB_PARTY_RESTART", off)
        # run.bat started without the launcher gets the same values through --write-env
        all_env = launcher.settings_env({"party_mode": "host", "party_restart": False})
        self.assertEqual(all_env["BB_PARTY_RESTART"], "0")
        self.assertEqual(all_env["BB_SKIP_NETWORK_CHOICE"], "online")


if __name__ == "__main__":
    unittest.main()
