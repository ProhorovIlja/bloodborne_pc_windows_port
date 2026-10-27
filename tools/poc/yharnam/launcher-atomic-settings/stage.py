#!/usr/bin/env python3
"""Source-exact Windows YT1.3 launcher atomic-settings experiment.

Original YT writes settings.json, mods.json, patches.json, bbport.ini and
offline news cache directly, risking partial JSON/INI on interrupted writes.
Keep all file formats, validation, keys, paths, auth and game code unchanged.
Only replace those direct writes with same-directory flushed temp + os.replace.
Inspired by reviewed NightwatchCoop commit a2cb365276419cc3985e05833809f0628193a190
("settings.json ... temp file and moved into place"), but independently
implemented and tested against exact *official YT 1.3.0* source/Windows.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = "bbport/launcher/bbport_launcher_win.py"
BLOB = "b54974c649610bef59e53a61ae294edc2d386cda"

INSERT = '''def atomic_utf8_write(path, text, encoding='utf-8'):
    """Replace a launcher-owned text file only AFTER its complete new bytes are
    written to the same filesystem. On any write/fsync/rename failure leave
    the preexisting file untouched; clean orphaned temp files.

    The caller owns its parent directory, and failures propagate so the UI
    does not mark unsaved changes as saved. Refuse symlink destinations to
    avoid silently breaking a user's linked configuration.
    """
    path = Path(path)
    if path.is_symlink():
        raise OSError(f'refusing to replace linked launcher settings: {path.name}')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding=encoding, newline='\\n', dir=str(path.parent),
                prefix=f'.{path.name}.', suffix='.tmp', delete=False) as out:
            temporary = Path(out.name)
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


'''

REPLACEMENTS = (
    ("def save_ini(values, lines):\n",
     INSERT + "def save_ini(values, lines):\n"),
    ("    ini_path().write_text('\\n'.join(out) + '\\n', encoding='utf-8')",
     "    atomic_utf8_write(ini_path(), '\\n'.join(out) + '\\n', encoding='utf-8')"),
    ("        CONFIG_FILE.write_text(json.dumps(self.app, indent=2, ensure_ascii=False), encoding='utf-8')",
     "        atomic_utf8_write(CONFIG_FILE, json.dumps(self.app, indent=2, ensure_ascii=False), encoding='utf-8')"),
    ("            (DATA_DIR / 'mods.json').write_text(json.dumps(",
     "            atomic_utf8_write(DATA_DIR / 'mods.json', json.dumps("),
    ("            (DATA_DIR / 'patches.json').write_text(json.dumps(",
     "            atomic_utf8_write(DATA_DIR / 'patches.json', json.dumps("),
    ("                    (CONFIG_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')",
     "                    atomic_utf8_write(CONFIG_DIR / name, json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')"),
)


def patch_text(original: str) -> str:
    if "def atomic_utf8_write(" in original:
        raise ValueError("Already patched")
    for before, after in REPLACEMENTS:
        if original.count(before) != 1:
            raise ValueError("Ambiguous or changed official native launcher source anchor: " +
                             before[:72])
        original = original.replace(before, after)
    return original


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN or git(root, "status", "--porcelain"):
        raise ValueError("Not clean pinned YT v1.3 source. No write.")
    if git(root, "rev-parse", "HEAD:" + PATH) != BLOB:
        raise ValueError("Unexpected launcher source blob. No write.")
    file = root / PATH
    modified = patch_text(file.read_text(encoding="utf-8"))
    file.write_bytes(modified.encode("utf-8"))  # LF, even on native Windows runner.
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_NATIVE_ATOMIC_LAUNCHER_SETTINGS_SOURCE_ONLY_STAGED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_pinned_official_yt_checkout", type=Path)
    apply(p.parse_args().disposable_pinned_official_yt_checkout)
