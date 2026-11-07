# SPDX-License-Identifier: GPL-3.0-or-later
"""V6: Yharnam Together launcher -> BBHost runtime (experimental).

The original Tk GUI stays the launcher. BBHost runs as its separate,
read-only-pinned native game host. This does NOT install seamless multiplayer:
the BBHost and YT account/room/world protocols differ. The old YT
BBPort path remains unchanged when the player selects BBPort.
No game assets, authentication tokens or signing seeds go to GitHub.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

EXPECTED_GAME_109 = "941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7"
MAX_ELF_BYTES = 256 * 1024 * 1024
MAX_CONFIG_BYTES = 2048
BACKENDS = ("bbport", "bbhost")


class EngineSetupError(ValueError):
    pass


def engine_file_v6(config_dir: Path) -> Path:
    return config_dir / "shyt-engine-v6.json"


def read_engine_v6(config_dir: Path) -> str:
    path = engine_file_v6(config_dir)
    if not path.exists() and not path.is_symlink():
        return "bbport"  # no BBHost runtime bridge advertised by default
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CONFIG_BYTES:
        raise EngineSetupError("Unsafe launcher engine selection file")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise EngineSetupError("Malformed launcher engine selection") from error
    if not isinstance(obj, dict) or set(obj) != {"engine"} or obj["engine"] not in BACKENDS:
        raise EngineSetupError("Unsupported launcher engine selection")
    return obj["engine"]


def write_engine_v6(config_dir: Path, value: str) -> None:
    if value not in BACKENDS:
        raise EngineSetupError("Unsupported engine")
    if config_dir.is_symlink():
        raise EngineSetupError("Unsafe launcher configuration directory")
    config_dir.mkdir(parents=True, exist_ok=True)
    target = engine_file_v6(config_dir)
    if target.is_symlink():
        raise EngineSetupError("Unsafe launcher engine selection file")
    # Write a separate complete file before replacement; no update servers
    # and no dangerous shell or arbitrary executable path in the setting.
    temp = config_dir / "shyt-engine-v6.json.new"
    if temp.exists() or temp.is_symlink():
        raise EngineSetupError("Launcher settings temporary file exists")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump({"engine": value}, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()


def host_binary_v6(port_dir: Path) -> Path:
    """Only the installed dedicated BBHost slot, not PATH/HTTP/JSON."""
    parent = port_dir / "bbhost"
    target = parent / "bbhost.exe"
    if port_dir.is_symlink() or parent.is_symlink() or target.is_symlink():
        raise EngineSetupError("BBHost installation must not be a symlink")
    if not parent.is_dir() or not target.is_file() or target.stat().st_size < 65536:
        raise EngineSetupError("Install the Windows BBHost release in the bbhost folder")
    if not str(target.resolve(strict=True)).lower().endswith("bbhost.exe"):
        raise EngineSetupError("Not the BBHost executable")
    with target.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise EngineSetupError("BBHost is not a Windows PE executable")
    return target.resolve(strict=True)


def owner_game_image_v6(settings: dict) -> tuple[Path, Path]:
    try:
        game = Path(settings["game_dir"]).resolve(strict=True)
    except (KeyError, TypeError, OSError) as error:
        raise EngineSetupError("Select a valid Bloodborne game folder") from error
    # V9: historical CUSA03173-patch/eboot.bin-decrypted was accepted by
    # BBHost. Search only explicit local game/update siblings, never disk.
    candidate_dirs = (game, game.parent / (game.name + "-patch"),
                      game.parent / (game.name + "-UPDATE"))
    seen = set()
    for directory in candidate_dirs:
        if directory != game and (directory.is_symlink() or not directory.is_dir()):
            continue
        for filename in ("eboot.bin-decrypted", "eboot.bin"):
            source = directory / filename
            if source in seen:
                continue
            seen.add(source)
            if source.is_symlink() or not source.is_file():
                continue
            size = source.stat().st_size
            if size < 65 or size > MAX_ELF_BYTES:
                continue
            digest = hashlib.sha256()
            with source.open("rb") as stream:
                if stream.read(5) != b"\x7fELF\x02":
                    continue  # wrapped/encrypted: never use it
                stream.seek(0)
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() == EXPECTED_GAME_109:
                return game, source.resolve(strict=True)
    raise EngineSetupError(
        "No supported decrypted Bloodborne 1.09 ELF found in selected "
        "game folder or adjacent -patch/-UPDATE folder. Check exact "
        "BBHost SHA-256; region and update names are not proof."
    )

def command_v6(port_dir: Path, data_dir: Path, settings: dict) -> list[str]:
    host = host_binary_v6(port_dir)
    game, executable = owner_game_image_v6(settings)
    data = data_dir / "user" / "bbhost"
    if data_dir.is_symlink() or data.is_symlink():
        raise EngineSetupError("Unsafe BBHost data directory")
    data.mkdir(parents=True, exist_ok=True)
    command = [str(host), "--app0", str(game), "--eboot", str(executable),
               "--data", str(data)]
    # Leave BBHost's own settings and authenticator in BBHost, rather
    # than passing shadNet passwords, keys or BBPort environment flags.
    local_config = data / "bbhost.toml"
    if local_config.is_symlink() or (local_config.exists() and not local_config.is_file()):
        raise EngineSetupError("Unsafe BBHost configuration")
    # The official BBHost default connects to a DIFFERENT public server.
    # A Seamless Hunt launch must never silently sign in there if the
    # private BBHost profile has not been configured yet.
    if not local_config.is_file():
        raise EngineSetupError(
            "Set up the separate BBHost profile (bbhost.toml) first. "
            "Refusing implicit third-party public server defaults. "
            "This experimental engine does not yet support YT seamless co-op."
        )
    command.extend(["--config", str(local_config)])
    return command


def launch_from_yt_v6(launcher, port_dir: Path, data_dir: Path) -> None:
    """Invoked by the REAL original Launcher.play, never before opt-in."""
    launcher.collect()
    try:
        command = command_v6(port_dir, data_dir, launcher.app)
        if launcher.process or launcher.installing:
            return
        log_path = Path(launcher.app.get("user_dir") or data_dir / "user") / "bbhost-last-run.log"
        # Existing launcher launch/log/exit handling is preserved, but the
        # guest executable is BBHost, not the original BBPort run.py.
        from_launcher_start = launcher._shyt_start_game_v6
        launcher.set_log("")
        launcher.process = from_launcher_start(command, dict(os.environ), log_path)
    except (EngineSetupError, OSError, ValueError) as error:
        launcher.messagebox.showerror("BBHost", str(error))
        return
    job = launcher._shyt_game_job_v6(launcher.process)
    launcher.job = job
    launcher._shyt_thread_v6(
        target=launcher.read_output,
        args=(launcher.process, job, log_path), daemon=True
    ).start()
    launcher.set_running(True, preparing=True)
    launcher.status.configure(
        text="BBHost starting (YT seamless multiplayer is NOT enabled in this pilot)",
        fg=launcher._shyt_status_color_v6
    )


def engine_settings_popup_v6(launcher, config_dir: Path, port_dir: Path) -> None:
    """The original YT GUI hosts this additional BBHost engine/settings tab."""
    import tkinter as tk  # a headless game's CLI or CI does not require Tk
    win = tk.Toplevel(launcher.root)
    win.title("Seamless Hunt | Game engine")
    win.transient(launcher.root)
    win.resizable(False, False)
    try:
        current = read_engine_v6(config_dir)
    except EngineSetupError as error:
        launcher.messagebox.showerror("Seamless Hunt", str(error))
        win.destroy()
        return
    selected = tk.StringVar(win, value=current)
    tk.Label(win, text="Game client engine", font=("Segoe UI", 12, "bold")).pack(
        padx=20, pady=(20, 8), anchor="w"
    )
    for value, label in (("bbhost", "BBHost (experimental, YT seamless not yet ported)"),
                         ("bbport", "Yharnam Together / BBPort (existing multiplayer)")):
        tk.Radiobutton(win, variable=selected, value=value, text=label).pack(
            padx=20, anchor="w"
        )
    tk.Label(
        win, justify="left", wraplength=470,
        text=("BBHost PC graphics, controls and plugins are configured in "
              "its own settings window. Updates must be signed: the YT/BBPort "
              "updater must NOT overwrite BBHost. This is not yet a merged co-op client.")
    ).pack(padx=20, pady=(12, 10), anchor="w")

    def open_bbhost_settings() -> None:
        try:
            executable = host_binary_v6(port_dir)
            subprocess.Popen([str(executable)], cwd=str(executable.parent),
                             stdin=subprocess.DEVNULL)
        except (OSError, EngineSetupError) as error:
            launcher.messagebox.showerror("BBHost", str(error))

    def save() -> None:
        try:
            write_engine_v6(config_dir, selected.get())
        except (OSError, EngineSetupError) as error:
            launcher.messagebox.showerror("Seamless Hunt", str(error))
            return
        win.destroy()

    buttons = tk.Frame(win)
    buttons.pack(padx=20, pady=(8, 20), fill="x")
    tk.Button(buttons, text="Open BBHost settings", command=open_bbhost_settings).pack(side="left")
    tk.Button(buttons, text="Save engine", command=save).pack(side="right")
    tk.Button(buttons, text="Cancel", command=win.destroy).pack(side="right", padx=6)
