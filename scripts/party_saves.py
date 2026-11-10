"""Safe, offline-only initial solo->party save copy with recoverable replacement.

Provenance: original ProhorovIlja/bloodborne_pc_windows_port party_saves.py
and a later upstream visy/bloodborne_pc_windows_port aside/rollback fix.
B67: old party data is never deleted; a unique .pending-replaced backup
survives every interruption of the two-rename promotion.

IMPORTANT: this is not a cross-process atomic directory swap or a coherent
snapshot of a game that is running. Launcher must not invoke during gameplay.
"""
import hashlib
import os
import shutil
import stat
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

SOLO = "savedata"
PARTY = "savedata_party"
BACKUPS = "save_backups"
LOCK = ".party-copy.lock"


def _real_dir(path: Path) -> bool:
    try:
        st = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(st.st_mode) or path.is_symlink():
        raise OSError(f"refusing symlink or non-directory: {path}")
    return True


def _files(folder: Path) -> dict:
    """Hash complete regular files, reject links, exclude incomplete .bbtmp."""
    if not _real_dir(folder):
        return {}
    result = {}
    for directory, subdirs, filenames in os.walk(folder, followlinks=False):
        parent = Path(directory)
        _real_dir(parent)
        for name in subdirs:
            _real_dir(parent / name)  # os.walk will not follow, but reject
        for name in sorted(filenames):
            path = parent / name
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode) or path.is_symlink():
                raise OSError(f"unsafe save-file entry: {path}")
            if name.endswith(".bbtmp"):
                continue
            h = hashlib.sha256()
            with path.open("rb") as stream:
                while data := stream.read(1024 * 1024):
                    h.update(data)
            result[path.relative_to(folder).as_posix()] = (path.stat().st_size, h.hexdigest())
    return result


def has_saves(folder: Path) -> bool:
    return bool(_files(Path(folder)))


def should_offer_copy(user: Path) -> bool:
    user = Path(user)
    return has_saves(user / SOLO) and not has_saves(user / PARTY)


@contextmanager
def _exclusive_copy(user: Path):
    # Never silently replace a leftover lock after process termination.
    # Manual recovery only after confirming no launcher or game is running.
    lock = user / LOCK
    with lock.open("x", encoding="utf-8") as f:
        f.write(f"created={time.time()}\npid={os.getpid()}\n")
        f.flush()
        os.fsync(f.fileno())
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def _backup_dir(user: Path) -> Path:
    root = user / BACKUPS
    if not _real_dir(root):
        root.mkdir()
    folder = root / PARTY
    if not _real_dir(folder):
        folder.mkdir()
    return folder


def _recover_interrupted(user: Path, folder: Path) -> None:
    """Never discard an earlier pending backup or guess among multiple ones."""
    party = user / PARTY
    pending = sorted(x for x in folder.glob("*.pending-replaced")
                     if x.is_dir() and not x.is_symlink())
    # Reject any symlink named like a previous pending backup.
    for x in folder.glob("*.pending-replaced"):
        if x.is_symlink() or not x.is_dir():
            raise OSError(f"invalid pending backup: {x}")
    if not pending:
        return
    if _real_dir(party):
        # An interrupted cleanup AFTER successful promotion. Preserve old
        # snapshots and merely rename them to a completed backup name.
        for x in pending:
            finished = x.with_name(x.name.removesuffix(".pending-replaced") + "-replaced")
            if finished.exists() or finished.is_symlink():
                raise FileExistsError(f"backup collision: {finished}")
            x.rename(finished)
        return
    if len(pending) != 1:
        raise RuntimeError("multiple interrupted party copies; manual inspection required")
    pending[0].rename(party)
    # Do not immediately replace the just-recovered party during this call.
    raise RuntimeError("interrupted party copy recovered; inspect saves and retry manually")


def _recover_pending_and_legacy(user: Path) -> None:
    """Under _exclusive_copy, restore or preserve old interrupted backups."""
    party = user / PARTY
    # Recovery always comes before source validation and before creating
    # staging, even if this attempt has no valid solo save anymore.
    backup_root = user / BACKUPS
    if backup_root.exists() or backup_root.is_symlink():
        _real_dir(backup_root)  # reject a symlinked ancestor as well
    backup_parent = backup_root / PARTY
    if backup_parent.exists() or backup_parent.is_symlink():
        _real_dir(backup_parent)
    # Upgrade path: visy's earlier fix used this fixed legacy aside.
    # Do not silently hide that save behind a newly copied solo save.
    legacy = user / (PARTY + ".replaced")
    if legacy.exists() or legacy.is_symlink():
        _real_dir(legacy)
        if not _real_dir(party):
            if backup_parent.is_dir() and list(backup_parent.glob("*.pending-replaced")):
                raise RuntimeError("ambiguous old and new interrupted party saves; inspect manually")
            legacy.rename(party)
            raise RuntimeError("legacy interrupted party copy restored; inspect and retry")
    if backup_parent.exists():
        _recover_interrupted(user, backup_parent)

def recover_interrupted_party_save(user: Path) -> bool:
    """Before starting a party game: repair only an unambiguous old save.

    Raises after recovery to force inspection before the game is allowed to
    start. A stale lock or multiple candidate backups blocks the launch,
    never silently discarding a possibly valid older party save.
    """
    user = Path(user)
    if not user.exists() and not user.is_symlink():
        return True  # first-ever party: game creates this profile on launch
    if not _real_dir(user):
        raise FileNotFoundError(f"invalid user directory: {user}")
    with _exclusive_copy(user):
        _recover_pending_and_legacy(user)
    return True


def copy_solo_to_party(user: Path, replace: bool = False):
    """Copy solo to party. Replace only if explicitly requested, never delete old.

    The only restore-on-error is renaming the PREVIOUS party directory back
    into place. A crash between directory renames leaves it in an obvious
    .pending-replaced backup, recoverable on next launcher invocation.
    """
    user = Path(user)
    if not _real_dir(user):
        raise FileNotFoundError(f"invalid user directory: {user}")
    with _exclusive_copy(user):
        solo, party = user / SOLO, user / PARTY
        _recover_pending_and_legacy(user)
        before = _files(solo)
        if not before:
            raise FileNotFoundError(f"no single-player saves in {solo}")
        party_exists = _real_dir(party)
        if party_exists and _files(party) and not replace:
            raise FileExistsError(f"{party} contains saves; explicit replace=True required")
        staging = Path(tempfile.mkdtemp(prefix=f".{PARTY}.copying-", dir=user))
        # Unique staging directory is created by mkdtemp (no reuse or
        # destructive cleanup of any stale user-owned staging path).
        try:
            shutil.copytree(solo, staging, ignore=shutil.ignore_patterns("*.bbtmp"),
                            dirs_exist_ok=True)
            if _files(staging) != before or _files(solo) != before:
                raise OSError("source or staged party save changed during verification")
            if party_exists:
                had_old_saves = bool(_files(party))
                folder = _backup_dir(user)
                _recover_interrupted(user, folder)
                token = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex
                pending = folder / (token + ".pending-replaced")
                finished = folder / (token + "-replaced")
                if pending.exists() or finished.exists():
                    raise FileExistsError("unique backup path unexpectedly occupied")
                # Atomic single-dir move on the same volume. NEVER remove
                # the existing party to make space and NEVER delete backups.
                party.rename(pending)
                try:
                    staging.rename(party)
                except OSError:
                    if not party.exists() and pending.exists():
                        try:
                            pending.rename(party)
                        except OSError:
                            # Old save is STILL safely in pending; caller
                            # must recover rather than start a fresh game.
                            pass
                    raise
                # Promotion succeeded; old backup remains valuable.
                try:
                    pending.rename(finished)
                except OSError:
                    return pending if had_old_saves else None  # intact and recoverable
                return finished if had_old_saves else None
            staging.rename(party)
            return None
        finally:
            if staging.exists():
                shutil.rmtree(staging)
