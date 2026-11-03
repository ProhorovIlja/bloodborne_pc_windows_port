#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V6 source-pinned patch for original Yharnam Together Windows Tk launcher.

The YT launcher remains the visible GUI. It gets an Engine dialog and,
only on explicit opt-in, launches a separately installed BBHost.exe.
The YT BBPort co-op path stays intact while real game/network integration
is developed. No YT updater may replace BBHost by accident.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "5d2305ee611ef1e03be39ff925f0da75c9a70393"
BLOB = "e881f2c0343371323fbb51798486bf6717d31401"
REL = "bbport/launcher/bbport_launcher_win.py"
MOD = "bbport/launcher/shyt_yt_bbhost_launcher_v6.py"


def once(src: str, before: str, after: str) -> str:
    if src.count(before) != 1:
        raise ValueError("YT Windows launcher source anchor changed")
    return src.replace(before, after, 1)


def modified(src: str) -> str:
    src = once(src,
       "import bbport_coop  # noqa: E402",
       "import bbport_coop  # noqa: E402\n"
       "import shyt_yt_bbhost_launcher_v6 as shyt_bbhost_v6  # noqa: E402"
    )
    src = once(src,
       "self.play_button.pack(side='right', padx=(px(8), px(24)))",
       "self.play_button.pack(side='right', padx=(px(8), px(24)))\n"
       "        # V6: original YT launcher remains the frontend; BBHost engine\n"
       "        # is an opt-in TEST baseline, not yet YT seamless multiplayer.\n"
       "        FlatButton(self, bar, 'Engine / BBHost',\n"
       "                   self.shyt_engine_popup_v6, bg=BG).pack(side='right', padx=px(5))"
    )
    methods = """    # V6: UI addon, no BBPort UI or co-op settings are deleted.
    def shyt_engine_popup_v6(self):
        shyt_bbhost_v6.engine_settings_popup_v6(self, CONFIG_DIR, PORT_DIR)

    def shyt_play_bbhost_v6(self):
        self._shyt_start_game_v6 = start_game
        self._shyt_game_job_v6 = GameJob
        self._shyt_thread_v6 = threading.Thread
        self._shyt_status_color_v6 = GOLD
        shyt_bbhost_v6.launch_from_yt_v6(self, PORT_DIR, DATA_DIR)

"""
    src = once(src, "    def play(self):", methods+"    def play(self):")
    src = once(src,
       """    def play(self):
        if self.process or self.installing:
            return
        if COOP_INSTALL:
""",
       """    def play(self):
        if self.process or self.installing:
            return
        # BBHost is deliberately a separately selected engine. It does
        # NOT get YT/BBPort's shadNet authorization or game-memory hooks.
        try:
            use_bbhost = shyt_bbhost_v6.read_engine_v6(CONFIG_DIR) == 'bbhost'
        except shyt_bbhost_v6.EngineSetupError as error:
            self.messagebox.showerror('Seamless Hunt', str(error))
            return
        if use_bbhost:
            self.shyt_play_bbhost_v6()
            return
        if COOP_INSTALL:
"""
    )
    # YT's updater is for BBPort binaries; NEVER let it destroy a
    # separately provisioned BBHost installation in this experiment.
    src=once(src,
       "    def coop_install_update(self):",
       """    def coop_install_update(self):
        if shyt_bbhost_v6.read_engine_v6(CONFIG_DIR) == 'bbhost':
            self.messagebox.showinfo(
                'BBHost updates',
                'BBHost must be updated by its own signed-release updater. '
                'The Yharnam Together BBPort updater is unavailable in BBHost mode.')
            return
"""
    )
    return src


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                       text=True, timeout=15)
    if p.returncode:
        raise ValueError("pinned YT checkout unavailable")
    return p.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-checkout", required=True, type=Path)
    parser.add_argument("--mode", choices=("check", "apply"), default="check")
    args = parser.parse_args()
    root = args.upstream_checkout.resolve(strict=True)
    original = root / REL
    module = Path(__file__).resolve().with_name("shyt_yt_bbhost_launcher_v6.py")
    dst = root / MOD
    if (git(root, "rev-parse", "HEAD") != PIN or
        git(root, "rev-parse", "HEAD:"+REL) != BLOB or
        original.is_symlink() or not original.is_file() or
        git(root,"hash-object",REL)!=BLOB or
        not module.is_file() or module.is_symlink()):
        raise ValueError("YT original Windows GUI or V6 module source drift")
    result = modified(original.read_text(encoding="utf-8"))
    if args.mode == "apply":
        if dst.exists() or dst.is_symlink() or dst.parent.is_symlink():
            raise ValueError("V6 launcher backend already patched")
        dst.write_bytes(module.read_bytes())
        original.write_text(result, encoding="utf-8")
    print("SHYT_V6_ACTUAL_YT_LAUNCHER_BBHOST_ENGINE_"+
          ("APPLIED" if args.mode=="apply" else "SOURCE_ANCHORS_PASS"))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise SystemExit("V6 refused original YT GUI patch: "+
                         type(exc).__name__) from None
