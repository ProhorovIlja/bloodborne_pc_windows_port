"""Isolated EXPERIMENTAL legacy BBSC launch opt-in for native Windows.

Never enabled by default or via persisted settings. The normal visy/BBP3 party
transport and offline startup stay untouched. The user must opt in in the GUI
again for each launcher session, and acknowledge risk before launch.

This only configures existing native runtime hooks. It does NOT claim a
working shadNet account login or CLS BBSC interoperability.
"""
from __future__ import annotations

from pathlib import Path
import os

# These are the exact feature gates consumed by src/runtime_legacy_net.c and
# upstream bbnet20 bbsc/core/bloodborne_re.cpp; not a new homebrew protocol.
BBSC_ENV = {
    "BB_BBSC": "1",
    "BB_LEGACY_NET": "1",
    # bbnet20 EmulatorSettings reads BB_ONLINE. Without this it loads but
    # deliberately stays disconnected (upstream SHADNET-PORT.md).
    "BB_ONLINE": "1",
    "BB_NET_BACKEND": "shadnet",
    "SHADPS4_BLOODBORNE_SEAMLESS_COOP": "1",
    "BB_SKIP_NETWORK_CHOICE": "online",
}
LEGACY_KEYS = ("BB_BBSC", "BB_LEGACY_NET", "BB_ONLINE", "BB_NET_BACKEND",
               "SHADPS4_BLOODBORNE_SEAMLESS_COOP", "BBSC_SAVE_DIR")


def clear_legacy_env(env: dict) -> None:
    """Ignore inherited host environment in ordinary launcher/warper modes."""
    for key in LEGACY_KEYS:
        env.pop(key, None)


def preflight(root: Path, *, party_mode: str, warper: bool = False) -> str | None:
    """Block experimental start unless an actual separately built DLL exists."""
    if warper:
        return "Legacy BBSC cannot run in world-warper/benchmark mode."
    if party_mode:
        return "Choose Solo first. Native Party and legacy BBSC are different online protocols."
    root = Path(root)
    engine = root / "out" / "bbport.exe"
    candidate = root / "out" / "gpu" / "bbnet20.dll"
    try:
        if root.is_symlink() or not root.is_dir():
            return "Cannot verify native Windows installation directory."
        if engine.is_symlink() or not engine.is_file() or engine.stat().st_size < 4096:
            return "Native bbport.exe missing or unverified. Install a real engine build first."
        if candidate.is_symlink() or not candidate.is_file() or candidate.stat().st_size < 4096:
            return ("Native bbnet20.dll candidate not installed. The ordinary Windows package "
                    "does not include this untested experimental module.")
        if candidate.parent.is_symlink():
            return "Experimental network DLL is inside a linked/untrusted folder."
    except OSError:
        return "Cannot read the native BBSC module and engine files."
    return None


def activate(env: dict) -> None:
    """Mutate only the launch-process environment after opt-in and preflight."""
    clear_legacy_env(env)
    env["BB_PARTY"] = ""
    env.update(BBSC_ENV)
    # This is not a save selector: only the native game's SaveData paths are
    # allowed by gpu/shim/bbsc_native_save_dir.h after loading the game SFO.
    # Inherited external BBSC_SAVE_DIR is explicitly ignored.
