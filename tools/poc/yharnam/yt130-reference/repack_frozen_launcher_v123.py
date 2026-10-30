#!/usr/bin/env python3
"""Replace ONLY the frozen BLauncher bundle in the exact validated internal YT 1.3 kit.

The native game and original vendor licenses remain byte-identical to the
known-good 2026-10-30 package. New BLauncher is built from source-exact
reviewed TLS/UTF8/discovery/atomic PR32 on original YT 1.3.0.
No production deployment or proprietary game assets. No network calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

ORIGINAL_SHA = "ee077748b3762db928d06718eea701fb1b0d0cedb0a3eac112bb9040ff0081bc"
REQUIRED = {
    "bbport-windows/Bloodborne.exe",
    "bbport-windows/BLauncher.exe",
    "bbport-windows/bin/bb-probe.exe",
    "bbport-windows/bin/bb-gpu-capabilities.exe",
    "bbport-windows/licenses/PkgTool-LICENSE.txt",
    "bbport-windows/licenses/Intel-XeSS-LICENSE.txt",
    "bbport-windows/licenses/FireBurn-FSR-Vulkan-LICENSE.txt",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check_archive(path: Path) -> set[str]:
    with ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) < 100 or len(infos) > 18000:
            raise ValueError("Unexpected original YT Windows bundle entry count")
        names = set()
        folded = set()
        size = 0
        for info in infos:
            name = info.filename
            parts = PurePosixPath(name).parts
            if (not name.startswith("bbport-windows/") or name.startswith("/")
                    or "\\" in name or "\x00" in name or ":" in name
                    or ".." in parts or any(not p for p in parts)):
                raise ValueError("Unsafe original kit archive name")
            if not info.is_dir():
                if name.casefold() in folded:
                    raise ValueError("Duplicate Windows-insensitive archive entry")
                names.add(name)
                folded.add(name.casefold())
                size += info.file_size
        if size > 3 * 1024**3 or not REQUIRED.issubset(names):
            raise ValueError("Missing original game/binary/license files or inflated archive")
        if archive.testzip() is not None:
            raise ValueError("Original kit CRC invalid")
    return names


def repack(original: Path, frozen: Path, output: Path, meta: Path) -> None:
    if digest(original) != ORIGINAL_SHA:
        raise ValueError("Not the exact source-verified original YT1.3 kit")
    orig_names = check_archive(original)
    if not (frozen / "BLauncher.exe").is_file():
        raise ValueError("Real rebuilt frozen launcher missing")
    if not (frozen / "_internal").is_dir():
        raise ValueError("Real PyInstaller onedir dependency folder missing")
    if output.resolve() == original.resolve():
        raise ValueError("Never rewrite original known-good kit in place")
    with tempfile.TemporaryDirectory(prefix="yt130-launcher-repack-") as td:
        stage = Path(td)
        with ZipFile(original) as z:
            z.extractall(stage)
        game = stage / "bbport-windows"
        old_launcher = digest(game / "BLauncher.exe")
        old_internal = game / "_internal"
        if not old_internal.is_dir():
            raise ValueError("Original frozen PyInstaller internal library bundle missing")
        shutil.rmtree(old_internal)
        for src in frozen.iterdir():
            dst = game / src.name
            if src.is_dir():
                if dst.exists():
                    raise ValueError("Unsafe new PyInstaller root collision: " + src.name)
                shutil.copytree(src, dst)
            elif src.is_file():
                if src.name != "BLauncher.exe" and dst.exists():
                    raise ValueError("Unexpected new root-level replacement: " + src.name)
                shutil.copy2(src, dst)
            else:
                raise ValueError("Frozen launcher contains non-file entry")
        new_launcher = digest(game / "BLauncher.exe")
        if old_launcher == new_launcher:
            raise ValueError("Rebuilt launcher EXE did not change")
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6,
                     allowZip64=True) as z:
            for file in sorted(stage.rglob("*")):
                if file.is_file():
                    if file.is_symlink():
                        raise ValueError("Refusing symlink in repacked install")
                    z.write(file, file.relative_to(stage).as_posix())
    new_names = check_archive(output)
    replaced = {"bbport-windows/BLauncher.exe"}
    replaced.update(n for n in orig_names if n.startswith("bbport-windows/_internal/"))
    for entry in orig_names - replaced:
        # Deep verify all native game code, settings, assets and licenses are
        # UNCHANGED, not merely present, without depending on file mtimes.
        with ZipFile(original) as a, ZipFile(output) as b:
            if entry not in new_names or hashlib.sha256(a.read(entry)).digest() != hashlib.sha256(b.read(entry)).digest():
                raise ValueError("Non-launcher original kit member was changed: " + entry)
    sha = digest(output)
    output.with_suffix(output.suffix + ".sha256").write_text(
        sha + "  " + output.name + "\n", encoding="ascii"
    )
    result = {
        "source_original_zip_sha256": ORIGINAL_SHA,
        "source_yt13_release": "0645740a33ae21c56df3b4a0d9777086dbca6053",
        "integrated_launcher_qa_pin": "df509976a3d013731b5377678d5bae4acfdf342c",
        "old_launcher_sha256": old_launcher,
        "new_launcher_sha256": new_launcher,
        "new_kit_sha256": sha,
        "original_game_and_vendor_files_byte_identical": True,
        "features_staged": ["Windows UTF8 and error logs", "Windows truststore TLS",
                            "game discovery", "atomic config writes"],
        "real_gameplay_tested": False,
        "direct_p2p_tested": False,
        "production_release": False,
    }
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SHYT_YT130_EXACT_GAME_UNCHANGED_INTEGRATED_LAUNCHER_REPACK_PASS", sha)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--original", type=Path, required=True)
    p.add_argument("--frozen", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--meta", type=Path, required=True)
    args = p.parse_args()
    repack(args.original, args.frozen, args.output, args.meta)
