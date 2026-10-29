#!/usr/bin/env python3
"""V104 surgical upstream improvements for the original Yharnam Together.

Based on review of lKaniel/bloodborne-server PR #433 (UTF-8 Windows
launcher child roles) and PR #451 (Ludwig exit multiplayer wall).
This deliberately avoids cherry-picking unrelated PR changes or touching
peer-to-peer gameplay networking. Both transforms reject source drift.
"""
from __future__ import annotations

PARTY = "emulator/src/core/bloodborne_party.cpp"
LAUNCHER = "bbport/launcher/bbport_launcher_win.py"
FILES = (PARTY, LAUNCHER)


def one(source: str, old: str, new: str, label: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise ValueError(f"V104 {label}: pinned source drift ({occurrences} anchors)")
    return source.replace(old, new, 1)


def patch_party(source: str) -> str:
    # The existing 18-wall registry is responsible for disabling phantom-only
    # barriers in a co-op session. Ludwig's exit is a separate event 13400010.
    source = one(
        source,
        """    // InitializeEvent(_, 7600, object, sfx) in m22-m35's event files (01.09).
    static constexpr std::array<s32, 18> Walls{
        2201999, 2301999, 2401999, 2401998, 2401997, 2401996, 2401995, 2411999, 2411998,
        2411997, 2421999, 2421998, 2701999, 2701998, 2801999, 2801998, 3201999, 3501990,
    };""",
        """    // Game event 13400010 also creates the multiplayer wall at Ludwig's
    // arena exit. Remove it in party sessions like the other 18 walls.
    static constexpr std::array<s32, 19> Walls{
        2201999, 2301999, 2401999, 2401998, 2401997, 2401996, 2401995, 2411999, 2411998,
        2411997, 2421999, 2421998, 2701999, 2701998, 2801999, 2801998, 3201999, 3401801,
        3501990,
    };""",
        "Ludwig multiplayer wall registry",
    )
    return source


def patch_launcher(source: str) -> str:
    # PyInstaller ignores PYTHONIOENCODING. When a Windows username/game path
    # contains Cyrillic, the run.py/mods.py role must not emit question marks
    # through the ANSI code page while the reader expects UTF-8.
    return one(
        source,
        """    for stream in (sys.stdout, sys.stderr):  # keep messages in order with the game's output
        try:
            stream.reconfigure(line_buffering=True)
        except (AttributeError, ValueError):
            pass""",
        """    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        except (AttributeError, ValueError):
            pass""",
        "UTF-8 frozen launcher script roles",
    )


def patch(files: dict[str, str]) -> dict[str, str]:
    if set(files) != set(FILES):
        raise ValueError("V104 requires exact launcher and party implementation")
    return {PARTY: patch_party(files[PARTY]),
            LAUNCHER: patch_launcher(files[LAUNCHER])}
