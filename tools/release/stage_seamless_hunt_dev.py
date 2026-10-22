"""Make a source-revision-stamped, game-file-free Seamless Hunt Windows dev kit.

Usage:
  python tools/release/stage_seamless_hunt_dev.py --source . \
      --output out/seamless-hunt-windows-dev.zip --revision <git-sha>

This is a *developer kit* with a self-contained CPython+Tk runtime, NOT an
approved full-BBSC production release or a production auto-updater.

Security: strict allowlist, rejects all symlinks, no savedata, config secrets,
game assets, user folders, logs or third-party executable downloads.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import zipfile


# A Windows portable archive that requires no separately installed Python.
# bbgpu is STATIC on Windows and is linked into bbport.exe, NOT a bbgpu.dll.
REQUIRED = (
    "out/bbport.exe",
    "launcher.py",
    "run.bat",
    "launch_gui.bat",
    "python/python.exe",
    "python/pythonw.exe",
    "python/python312.dll",
    "python/LICENSE.txt",
    "python/LICENSE-tcltk.txt",
)

OPTIONAL = (
    "out/bb-probe.exe",
    "out/bb-gpu-capabilities.exe",
    "VERSION",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "README.ru.md",
    "docs/PARTY.md",
)

DIRECTORY_SUFFIXES = {
    "scripts": frozenset((".py",)),
    "patches": frozenset((".xml", ".json")),
    "launcher": frozenset((".py", ".ico", ".png")),
    "licenses": frozenset((".txt", ".md")),
}
LICENSE_BASENAMES = frozenset(("license", "copying", "notice", "patents"))
DOC = """Seamless Hunt PC - NATIVE WINDOWS DEVELOPER BUILD

This artifact is built from the fork's commit described in MANIFEST.json.
It contains NO Bloodborne game files and NO save data or account credentials.
Only use your own Bloodborne v1.09 game dump. The native runtime executes
the game's x86-64 code and translates graphics into Vulkan.

This is not yet a production-ready BBSC release:
- Windows 10/11 x64, supported CPU, Vulkan graphics drivers are required.
- Double-click launch_gui.bat. Python 3.12/Tk is BUNDLED; no separate Python install.
- Direct P2P gameplay is visy's existing implementation. BBSC/shadNet
  account check and private-server registration are short-lived launcher
  operations: they do NOT log the GAME in or provide legacy BBSC matchmaking.
- Choose a realm hostname in the launcher; it currently affects diagnostics
  and account screens, not the native gameplay network stack.
- The included Network Doctor is optional; STUN shares your public IP/port
  with the chosen STUN provider when you click the test.
- Game compatibility, live P2P and GPU performance MUST be tested on real PCs.

Do NOT merge this into an existing Bloodborne installation. Extract to its
own directory and point the launcher at your own game folder.
Do not upload saves or credentials in a bug report.
"""


def _safe_file(base: Path, rel: str) -> Path:
    posix = PurePosixPath(rel)
    if posix.is_absolute() or ".." in posix.parts:
        raise ValueError("Package path traversal is forbidden")
    obj = base.joinpath(*posix.parts)
    if not obj.is_file() or obj.is_symlink():
        raise ValueError(f"Missing file or symlink in package: {rel}")
    return obj


def _collect(source: Path, include_native_bbsc: bool = False) -> dict[str, Path]:
    out = {rel: _safe_file(source, rel) for rel in REQUIRED}
    if include_native_bbsc:
        # Explicitly opted-in experimental game-less build, never part of
        # normal user distributions and never a wildcard GPU/build tree.
        out["out/gpu/bbnet20.dll"] = _safe_file(source, "out/gpu/bbnet20.dll")
    for rel in OPTIONAL:
        obj = source.joinpath(*PurePosixPath(rel).parts)
        if obj.is_file() and not obj.is_symlink():
            out[rel] = obj
    # Scripts, official XML patches, artwork and GPL notices: never walk
    # arbitrary user/ or mods/ trees even if they live beside the code.
    for directory in ("scripts", "patches", "launcher", "licenses"):
        folder = source / directory
        if not folder.is_dir():
            continue
        for obj in folder.rglob("*"):
            if not obj.is_file() or obj.is_symlink():
                continue
            if (obj.suffix.lower() not in DIRECTORY_SUFFIXES[directory]
                    and not (directory == "licenses" and obj.name.lower() in LICENSE_BASENAMES)):
                continue
            rel = obj.relative_to(source).as_posix()
            if "__pycache__" in obj.parts or obj.name.startswith("."):
                continue
            out[rel] = obj
    # CPython/Tcl/Tk is staged by the trusted release tool; a closed set of
    # directories and root binaries prevents accidentally publishing a user's
    # secrets from an adjacent working tree or arbitrary site-packages.
    runtime = source / "python"
    allowed_root = {"python.exe", "pythonw.exe", "python3.dll", "python312.dll",
                    "vcruntime140.dll", "vcruntime140_1.dll", "LICENSE.txt",
                    "LICENSE-tcltk.txt", "README.txt"}
    allowed_trees = {"Lib", "DLLs", "tcl"}
    for obj in runtime.rglob("*"):
        if obj.is_symlink():
            raise ValueError(f"Python bundle contains symlink: {obj}")
        if not obj.is_file():
            continue
        rel = obj.relative_to(runtime)
        if len(rel.parts) == 1:
            if rel.name not in allowed_root:
                raise ValueError(f"Unexpected Python root file: {rel}")
        elif rel.parts[0] not in allowed_trees or "site-packages" in rel.parts:
            raise ValueError(f"Unexpected Python runtime file: {rel}")
        if obj.suffix.lower() in {".key", ".pfx", ".pem"}:
            raise ValueError(f"Refusing credential-like file in Python bundle: {rel}")
        out["python/" + rel.as_posix()] = obj
    if not (runtime / "Lib" / "tkinter" / "__init__.py").is_file():
        raise ValueError("Python bundle has no tkinter; cannot launch GUI offline")
    # Runtime DLL legal notices from scripts/stage_licenses.py live in
    # out/licenses, NOT the repo's top-level licenses directory. Earlier
    # developer ZIPs accidentally omitted these notices.
    notices = source / "out" / "licenses"
    if not (notices / "LICENSE").is_file():
        raise ValueError("Staged runtime licence inventory missing: out/licenses/LICENSE")
    for obj in notices.rglob("*"):
        if obj.is_symlink():
            raise ValueError(f"Symlink forbidden in staged runtime licences: {obj}")
        if obj.is_file():
            rel = obj.relative_to(source).as_posix()
            if obj.name.startswith(".") or obj.suffix.lower() in {".exe", ".dll", ".key", ".pfx", ".pem"}:
                raise ValueError(f"Unexpected file in staged runtime licences: {rel}")
            out[rel] = obj
    # Windows build links bbgpu STATIC into bbport.exe. Dependency DLLs are
    # explicitly staged beside the executable, never in out/gpu/ or below.
    # rglob() here accidentally included arbitrary nested build-tree DLLs.
    folder = source / "out"
    for obj in folder.glob("*.dll"):
        if obj.is_file() and not obj.is_symlink():
            out[obj.relative_to(source).as_posix()] = obj
    return out


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def pack(source: Path, destination: Path, revision: str,
         *, include_native_bbsc: bool = False) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Revision must be a 40-character Git commit SHA")
    source = source.resolve(strict=True)
    destination = destination.resolve()
    collected = _collect(source, include_native_bbsc=include_native_bbsc)
    # Refuse package output within itself, and never include the user's game.
    if any(destination == obj.resolve() for obj in collected.values()):
        raise ValueError("Output overlaps a packaged file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as output:
        for rel, obj in sorted(collected.items()):
            data = obj.read_bytes()
            entries.append({"path": rel, "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
            output.writestr(_zip_info(rel), data)
        metadata = {"format": "seamless-hunt-native-windows-dev-v2",
                    "source_commit": revision, "files": entries,
                    "native_bbsc_candidate_included": include_native_bbsc}
        output.writestr(_zip_info("MANIFEST.json"),
                        (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        candidate_warning = (
            "\nEXPERIMENTAL CLS BBSC DLL IS INCLUDED IN THIS CANDIDATE.\n"
            "It is NOT validated for live server login, bell matchmaking or\n"
            "cross-play. Use an isolated game/save copy and unique account.\n"
            "The ordinary developer ZIP excludes bbnet20.dll entirely.\n"
        ) if include_native_bbsc else ""
        output.writestr(_zip_info("README-DEVELOPER-BUILD.txt"),
                        (DOC + candidate_warning).encode("utf-8"))
    return {"source_commit": revision, "files": len(collected),
            "native_bbsc_candidate_included": include_native_bbsc,
            "archive": str(destination), "bytes": destination.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--include-native-bbsc-candidate", action="store_true",
                        help="Include out/gpu/bbnet20.dll in explicitly experimental test ZIP")
    args = parser.parse_args()
    try:
        result = pack(args.source, args.output, args.revision,
                      include_native_bbsc=args.include_native_bbsc_candidate)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
