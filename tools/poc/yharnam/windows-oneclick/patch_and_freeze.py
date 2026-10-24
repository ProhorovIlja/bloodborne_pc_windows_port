#!/usr/bin/env python3
"""Freeze a fixed-port Yharnam Together BLauncher.exe for the isolated Seamless Hunt PoC."""
import argparse, ast, pathlib, subprocess, sys

PIN = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"
PORT_LINE = "SHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = 31313, 31315, 31314, 20443"
PORT_POC = "# SH_YT_ONECLICK_PATCH_20261023\nSHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = 32313, 32315, 32314, 21443"
PROFILE_LINE = "('bbport-launcher-coop' if COOP_TEST else 'bbport-launcher')"
PROFILE_POC = "('bbport-launcher-coop-shpoc' if COOP_TEST else 'bbport-launcher-shpoc')"
COOP_UPDATES = "def fetch_releases(timeout=15):"
NORMAL_UPDATES = "def fetch_update_release(beta=False):"

def replace_once(source, old, new, name):
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{name}: upstream anchor count {count} (expected 1)")
    return source.replace(old, new, 1)

def load_release_channel():
    import importlib.util
    path = pathlib.Path(__file__).resolve().parents[1] / "release-v8" / "patch_update_channel.py"
    spec = importlib.util.spec_from_file_location("sh_yt_release_channel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patch_coop(source, release_channel=False):
    source = replace_once(source, PORT_LINE, PORT_POC, "port constants")
    if release_channel:
        source = load_release_channel().patch_coop(source)
    else:
        source = replace_once(source, COOP_UPDATES, COOP_UPDATES + "\n    return []  # PoC: updater disabled", "co-op updater")
    source = source.replace("port 20443 doesn't answer", "port 21443 doesn't answer")
    ast.parse(source)
    return source

def patch_launcher(source, release_channel=False):
    if release_channel:
        return load_release_channel().patch_launcher(source)
    source = replace_once(source, PROFILE_LINE, PROFILE_POC, "profile isolation")
    source = replace_once(source, NORMAL_UPDATES, NORMAL_UPDATES + "\n    return None  # PoC: updater disabled", "general updater")
    source = replace_once(source, "'check_updates': True, 'animations'", "'check_updates': False, 'animations'", "update preference")
    ast.parse(source)
    return source

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--release-channel", action="store_true", help="Use Seamless Hunt protocol-gated GitHub Releases")
    args = parser.parse_args()
    repo = args.checkout.resolve()
    actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    if actual != PIN:
        raise SystemExit(f"Wrong upstream revision {actual} (expected {PIN})")
    for path, patch in {
        repo / "bbport/launcher/bbport_coop.py": patch_coop,
        repo / "bbport/launcher/bbport_launcher_win.py": patch_launcher,
    }.items():
        path.write_text(patch(path.read_text(encoding="utf-8"), args.release_channel), encoding="utf-8", newline="\n")
    launcher = repo / "bbport/launcher/bbport_launcher_win.py"
    icon = repo / "bbport/launcher/bloodborne.ico"
    assert launcher.is_file() and icon.is_file()
    args.out.mkdir(parents=True, exist_ok=True)
    hidden = "argparse base64 bisect collections contextlib hashlib json re shutil struct tempfile xml.etree.ElementTree urllib.request ctypes.wintypes binascii datetime http.server secrets sqlite3 uuid zlib bbport_icons".split()
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
        "--windowed", "--onedir", "--name", "BLauncher", "--icon", str(icon),
        "--distpath", str(args.out), "--workpath", str(args.out.parent / "pyi-work"),
        "--specpath", str(args.out.parent / "pyi-spec"), "--paths", str(repo / "bbport/launcher")]
    for item in hidden:
        command.extend(["--hidden-import", item])
    command.append(str(launcher))
    subprocess.run(command, check=True)
    exe = args.out / "BLauncher/BLauncher.exe"
    if not exe.is_file():
        raise SystemExit("PyInstaller did not produce BLauncher.exe")
    print("BLAUNCHER BUILD PASS:", exe)

if __name__ == "__main__":
    main()
