#!/usr/bin/env python3
"""Backport original YT PR #433 Windows Unicode/startup diagnostics to pinned YT 1.3.

Preserves the upstream-author patch unmodified for provenance. Source exact
backport applies only the same reviewed hunks to original v1.3.0 launcher,
not the newer PR branch's other source. No client release, save, auth or wire
modifications. Import author's new Windows functional tests unchanged.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE = "bbport/launcher/bbport_launcher_win.py"
BLOB = "b54974c649610bef59e53a61ae294edc2d386cda"
ADDED_TEST = "bbport/tests/test_launcher_code_page.py"
PATCH = Path(__file__).with_name("upstream-YT-PR433.patch")
HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.M)

OLD_STDIO = """    for stream in (sys.stdout, sys.stderr):  # keep messages in order with the game's output
        try:
            stream.reconfigure(line_buffering=True)
        except (AttributeError, ValueError):
            pass"""
NEW_STDIO = """    # UTF-8 whatever the Windows code page, as run.py reads it: a frozen launcher ignores PYTHONIOENCODING, and
    # on a Russian Windows mods.py's game view path reached run.py as '????' (Kaniel 2026-10-27: Cyrillic user
    # names, "the game doesn't start at all"). Line by line, to keep messages in order with the game's output.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        except (AttributeError, ValueError):
            pass"""

OLD_ROLE_EXCEPTION = """    except SystemExit as stop:
        return stop.code if isinstance(stop.code, int) else (0 if stop.code is None else 1)
    return 0"""
NEW_ROLE_EXCEPTION = """    except SystemExit as stop:
        if stop.code is None or isinstance(stop.code, int):
            return stop.code or 0
        print(stop.code, file=sys.stderr)  # sys.exit('message'), as python prints it
        return 1
    except Exception:  # into the log: frozen, it was PyInstaller's popup and an empty log
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1
    return 0"""

OLD_MAIN = """def main():
    global LANG"""
NEW_MAIN = """def main():
    \"\"\"start_launcher, with any failure (Tcl that cannot start, --play, the uninstaller, an update) written to
    user/log/launcher-errors.txt and shown: frozen and windowed, an uncaught error was only PyInstaller's popup,
    and before the window no log was kept at all (Kaniel 2026-10-27: "writes 0 logs").\"\"\"
    try:
        start_launcher()
    except SystemExit:
        raise
    except BaseException:
        import traceback
        details = traceback.format_exc()
        log = record_startup_failure(details)
        where = str(log) if log else _('no log could be written', 'журнал записать не удалось')
        show_error_box(_('The launcher could not start. The details are in:\\n{}\\n\\n{}',
                         'Лаунчер не смог запуститься. Подробности в файле:\\n{}\\n\\n{}').format(where, details[-1500:]))
        sys.exit(1)


def record_startup_failure(text):
    \"\"\"Adds TEXT to user/log/launcher-errors.txt, or to %TEMP% when that folder cannot be written (an install
    under Program Files, a read-only drive). Returns the file written, None when neither could be.\"\"\"
    stamp = f'--- launcher failed {time.strftime("%Y-%m-%d %H:%M:%S")} (command-line arguments withheld for privacy)\\n'
    for log in (DATA_DIR / 'user' / 'log' / 'launcher-errors.txt',
                Path(tempfile.gettempdir()) / 'BLauncher-errors.txt'):
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            with open(log, 'a', encoding='utf-8') as file:
                file.write(stamp + text + ('' if text.endswith('\\n') else '\\n'))
            return log
        except OSError:
            continue
    return None


def show_error_box(text):
    try:
        ctypes.windll.user32.MessageBoxW(None, text, COOP_NAME if COOP_INSTALL else 'Bloodborne', 0x10)  # MB_ICONERROR
    except (AttributeError, OSError):
        pass


def start_launcher():
    global LANG"""

OLD_TK = """    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    root = tk.Tk()
    keep_launcher_errors(root)
    Launcher(root, tk, ttk, filedialog, messagebox)
    root.mainloop()"""
NEW_TK = """    log = open_launcher_errors()  # before Tk: a crash while Tcl starts leaves its trace too
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        root = tk.Tk()
        keep_launcher_errors(root, log)
        Launcher(root, tk, ttk, filedialog, messagebox)
        root.mainloop()
    finally:
        if log is not None:  # main() appends what went wrong to the same file
            import faulthandler
            faulthandler.disable()
            log.close()"""

OLD_KEEP_ERRORS = """def keep_launcher_errors(root):
    \"\"\"The windowed launcher has no console: a fault of the process and an error in a window callback go
    to user/log/launcher-errors.txt, so a crash leaves its cause behind (Kaniel 2026-10-17).\"\"\"
    import faulthandler
    import traceback
    try:
        folder = DATA_DIR / 'user' / 'log'
        folder.mkdir(parents=True, exist_ok=True)
        log = open(folder / 'launcher-errors.txt', 'a', encoding='utf-8', buffering=1)
    except OSError:
        return
    log.write(f'--- launcher started {time.strftime("%Y-%m-%d %H:%M:%S")}\\n')
    faulthandler.enable(log)

    def report(kind, value, trace):
        log.write(''.join(traceback.format_exception(kind, value, trace)))
    root.report_callback_exception = report
    root.launcher_errors = log  # kept open for faulthandler while the window lives"""
NEW_KEEP_ERRORS = """def open_launcher_errors():
    \"\"\"user/log/launcher-errors.txt, open for the window's life with faulthandler writing to it; None when it
    cannot be opened.\"\"\"
    import faulthandler
    try:
        folder = DATA_DIR / 'user' / 'log'
        folder.mkdir(parents=True, exist_ok=True)
        log = open(folder / 'launcher-errors.txt', 'a', encoding='utf-8', buffering=1)
    except OSError:
        return None
    log.write(f'--- launcher started {time.strftime("%Y-%m-%d %H:%M:%S")}\\n')
    faulthandler.enable(log)
    return log


def keep_launcher_errors(root, log):
    \"\"\"The windowed launcher has no console: a fault of the process and an error in a window callback go
    to user/log/launcher-errors.txt, so a crash leaves its cause behind (Kaniel 2026-10-17).\"\"\"
    import traceback
    if log is None:
        return

    def report(kind, value, trace):
        log.write(''.join(traceback.format_exception(kind, value, trace)))
    root.report_callback_exception = report
    root.launcher_errors = log  # kept open for faulthandler while the window lives"""

REBASE = ((OLD_STDIO, NEW_STDIO),
          (OLD_ROLE_EXCEPTION, NEW_ROLE_EXCEPTION),
          (OLD_MAIN, NEW_MAIN),
          (OLD_TK, NEW_TK),
          (OLD_KEEP_ERRORS, NEW_KEEP_ERRORS))


def validate(patch: str):
    pairs = HEADER.findall(patch)
    if len(pairs) != 2 or any(a != b for a, b in pairs):
        raise ValueError("Unexpected changed file names")
    if {a for a, b in pairs} != {FILE, ADDED_TEST}:
        raise ValueError("Patch contains unauthorized file paths")
    for token in ("reconfigure(encoding='utf-8', errors='replace', line_buffering=True)",
                  "launcher-errors.txt", "faulthandler", "record_startup_failure",
                  "CYRILLIC", "test_a_script_prints_a_cyrillic_path_in_utf8",
                  "test_a_failure_before_the_window_is_logged_and_shown",
                  "test_the_log_goes_to_temp_when_the_install_cannot_be_written"):
        if token not in patch:
            raise ValueError("Missing original author change/test " + token)


def backport(source: str) -> str:
    for old, new in REBASE:
        if source.count(old) != 1:
            raise ValueError("Changed native YT1.3 source: required unique anchor missing")
        source = source.replace(old, new)
    return source


def original_tests(patch: str) -> str:
    section = patch.split("diff --git a/" + ADDED_TEST + " b/" + ADDED_TEST + "\n")
    if len(section) != 2:
        raise ValueError("Original upstream test hunk missing")
    body = section[1].split("@@ -0,0 +1,126 @@", 1)
    if len(body) != 2:
        raise ValueError("Unexpected original author test lines")
    lines = [line[1:] for line in body[1].splitlines()
             if line.startswith("+") and not line.startswith("+++")]
    if len(lines) != 126:
        raise ValueError("Missing original upstream six Windows test cases")
    return "\n".join(lines) + "\n"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path):
    root = root.resolve()
    patch = PATCH.read_text(encoding="utf-8")
    validate(patch)
    if git(root, "rev-parse", "HEAD") != PIN or git(root, "status", "--porcelain"):
        raise ValueError("Not original clean official YT1.3 source")
    if git(root, "rev-parse", "HEAD:" + FILE) != BLOB:
        raise ValueError("Wrong native launcher SHA")
    test_path = root / ADDED_TEST
    if test_path.exists():
        raise ValueError("Unexpected official test file already exists")
    f = root / FILE
    rebase = backport(f.read_text(encoding="utf-8"))
    tests = original_tests(patch)
    # All source validation above completes before either file can be modified.
    # On Windows write_text() translates LF into CRLF, making pinned Git
    # diffs fail whitespace checks. Preserve original repository LF bytes.
    f.write_bytes(rebase.encode("utf-8"))
    test_path.write_bytes(tests.encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_PR433_SOURCE_EXACT_ADAPTED_UTF8_LOGS_AND_AUTHOR_TESTS_STAGED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_yt130_checkout)
