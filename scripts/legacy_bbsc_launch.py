"""Isolated EXPERIMENTAL legacy BBSC launch opt-in for native Windows.

Never enabled by default or via persisted settings. The normal visy/BBP3 party
transport and offline startup stay untouched. The user must opt in in the GUI
again for each launcher session, and acknowledge risk before launch.

This only configures existing native runtime hooks. It does NOT claim a
working shadNet account login or CLS BBSC interoperability.
"""
from __future__ import annotations

from pathlib import Path
import json
import os
import re
import tempfile

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
               "BB_NET_GEN", "SHADPS4_BLOODBORNE_SEAMLESS_COOP", "BBSC_SAVE_DIR",
               "BB_SHADNET_SERVER", "BB_SHADNET_WEBAPI", "BB_SHADNET_NPID",
               "BB_SHADNET_PASSWORD", "BB_SHADNET_TOKEN", "BB_COMMUNITY_SERVER",
               "SHADPS4_HTTP_HOST_OVERRIDES_JSON")


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


REALM_RE = re.compile(
    r"(?=.{1,253}\Z)[A-Za-z0-9]+(?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9]+(?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\Z")
ACCOUNT_RE = re.compile(r"[A-Za-z0-9_-]{1,32}\Z")
GAME_SERVER = "https://ss4.scej-network.jp:20443"


def validate_credentials(realm: str, account: str, password: str) -> str:
    """Return canonical realm or raise with a user-facing explanation."""
    if not isinstance(realm, str) or not REALM_RE.fullmatch(realm.strip()):
        raise ValueError("Invalid shadNet host: enter a DNS name or IPv4 address only")
    if not isinstance(account, str) or not ACCOUNT_RE.fullmatch(account):
        raise ValueError("NP ID must contain 1-32 letters, numbers, _ or -")
    if (not isinstance(password, str) or not password
            or len(password.encode("utf-8")) > 1024 or "\0" in password):
        raise ValueError("Password must be 1-1024 UTF-8 bytes without NUL")
    return realm.strip().lower()


def configure_realm(env: dict, root: Path, *, host: str, account: str,
                    password: str) -> Path:
    """Bind shadNet, WebAPI, and the game's own HTTPS server for this launch.

    This mirrors the *shadNet pool* from deadinside28/run.sh and
    scripts/online.py, NOT The Hunter's Dream/THD backend. One new JSON file in
    out/ contains ONLY a public game URL redirect. Never store credentials.
    """
    realm = validate_credentials(host, account, password)
    output = Path(root) / "out"
    if not output.is_dir() or output.is_symlink():
        raise ValueError("Native client output directory is missing or linked")
    if realm in ("play.seamlesshunt.com", "localhost", "127.0.0.1"):
        community = "http://" + realm
    else:
        community = "https://" + realm
    override = {GAME_SERVER: community}
    # Unique file prevents cross-launch conflicts. No retail game assets,
    # session token, password or save path is ever written to this file.
    with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output,
            prefix="bbsc-host-", suffix=".json", delete=False) as file:
        json.dump(override, file, indent=2)
        file.write("\n")
        filepath = Path(file.name)
    env.update({
        "BB_SHADNET_SERVER": realm + ":31313",
        "BB_SHADNET_WEBAPI": "http://" + realm + ":31315",
        "BB_COMMUNITY_SERVER": community,
        "BB_SHADNET_NPID": account,
        "BB_SHADNET_PASSWORD": password,
        "SHADPS4_HTTP_HOST_OVERRIDES_JSON": str(filepath),
        "BB_NET_GEN": "20",
    })
    return filepath
