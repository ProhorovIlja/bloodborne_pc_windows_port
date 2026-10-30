#!/usr/bin/env python3
"""Metadata-only DS3 PC/BB reference inventory; no game content is read.

DS3 BDTs are opaque here. No extraction, network, EXE read, hashes,
modification or copying. Output never contains user paths or filenames.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

SCHEMA = "SHYT_DS3_PC_REFERENCE_V154"
BB_SCHEMA = "SHYT_NATIVE_ASSET_INVENTORY_V1"
MAX_FILES = 350000
MAX_REPORT_BYTES = 2 * 1024 * 1024
ARCHIVES = tuple(f"Data{i}" for i in range(6))
FAMILIES = {
    "binder": {".bnd", ".bnd4", ".chrbnd", ".anibnd", ".objbnd"},
    "compression": {".dcx"},
    "world_events": {".emevd", ".evd", ".esd", ".msb"},
    "meshes": {".flver", ".flv"},
    "textures": {".tpf", ".dds"},
    "params": {".param", ".paramdef", ".gparam", ".mtd"},
    "animation_physics": {".tae", ".hkx", ".nva"},
    "pc_shaders": {".fxo", ".vso", ".ppo", ".fpo", ".shaderbnd"},
}

class InventoryError(ValueError):
    pass

def game_root(path: Path) -> Path:
    root = path.resolve(strict=True)
    if not root.is_dir():
        raise InventoryError("DS3 input must be a directory")
    for candidate in (root, root / "Game"):
        if candidate.is_symlink():
            continue
        exe = candidate / "DarkSoulsIII.exe"
        if exe.is_file() and not exe.is_symlink():
            return candidate
    raise InventoryError("DarkSoulsIII.exe not found in selected Game folder")

def bb_extensions(path: Path) -> dict[str, int]:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_REPORT_BYTES:
        raise InventoryError("invalid Bloodborne metadata report")
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError):
        raise InventoryError("invalid Bloodborne metadata JSON") from None
    if not isinstance(report, dict) or report.get("schema") != BB_SCHEMA:
        raise InventoryError("expected V146 Bloodborne metadata-only report")
    if not isinstance(report.get("privacy"), dict) or (
            report["privacy"].get("relative_paths_included") is not False):
        raise InventoryError("Bloodborne report must exclude filenames")
    ext = report.get("extensions")
    if not isinstance(ext, list) or len(ext) > 2000:
        raise InventoryError("invalid Bloodborne extension summary")
    result: dict[str, int] = {}
    for row in ext:
        if not isinstance(row, dict):
            raise InventoryError("invalid Bloodborne extension row")
        suffix, n = row.get("extension"), row.get("files")
        if not isinstance(suffix, str) or (suffix != "(none)" and (
                not suffix.startswith(".") or len(suffix) > 32)):
            raise InventoryError("invalid Bloodborne extension type")
        if type(n) is not int or n < 0 or n > MAX_FILES or suffix in result:
            raise InventoryError("invalid Bloodborne extension count")
        result[suffix] = n
    return result

def inventory(path: Path, bloodborne_report: Path | None = None) -> dict:
    root = game_root(path)
    bb_ext = bb_extensions(bloodborne_report) if bloodborne_report is not None else None
    extensions: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    lower_names = set()
    symlinks = conflicts = files_count = total_bytes = 0

    def onerror(_error: OSError) -> None:
        raise InventoryError("some DS3 files could not be enumerated") from None

    for folder, dirs, files in os.walk(root, topdown=True, followlinks=False,
                                      onerror=onerror):
        base = Path(folder)
        clean_dirs = []
        for name in sorted(dirs):
            p = base / name
            if p.is_symlink():
                symlinks += 1
            else:
                clean_dirs.append(name)
        dirs[:] = clean_dirs
        for name in sorted(files):
            p = base / name
            if p.is_symlink():
                symlinks += 1
                continue
            if not p.is_file():
                continue
            try:
                size = p.stat().st_size
            except OSError:
                raise InventoryError("a DS3 file became unreadable") from None
            rel = p.relative_to(root).as_posix().casefold()
            if rel in lower_names:
                conflicts += 1
            lower_names.add(rel)
            ext = p.suffix.lower() or "(none)"
            extensions[ext] += 1
            extension_bytes[ext] += size
            files_count += 1
            total_bytes += size
            if files_count > MAX_FILES:
                raise InventoryError("DS3 inventory file count exceeded bound")
    archive_pairs = {
        stem: {
            "index_present": (root / f"{stem}.bhd").is_file() and not (root / f"{stem}.bhd").is_symlink(),
            "data_present": (root / f"{stem}.bdt").is_file() and not (root / f"{stem}.bdt").is_symlink(),
        }
        for stem in ARCHIVES
    }
    report = {
        "schema": SCHEMA,
        "privacy": {
            "game_bytes_uploaded": False,
            "game_contents_read": False,
            "absolute_paths_included": False,
            "relative_paths_included": False,
            "file_hashes_included": False,
        },
        "game_executable_present": True,
        "files": files_count,
        "bytes": total_bytes,
        "extensions": [
            {"extension": ext, "files": extensions[ext], "bytes": extension_bytes[ext]}
            for ext in sorted(extensions)
        ],
        "known_archives": archive_pairs,
        "known_dirs": {
            d: (root / d).is_dir() and not (root / d).is_symlink()
            for d in ("sound", "movie")
        },
        "symlinks_skipped": symlinks,
        "case_insensitive_path_collisions": conflicts,
        "observability": "Visible files only; DS3 BDT/BND contents and shaders are not counted",
        "executable_version_verified": False,
        "engine_compatibility_proven": False,
    }
    if bb_ext is not None:
        report["bloodborne_comparison"] = {
            "report_schema": BB_SCHEMA,
            "family_visible_file_counts": [
                {"family": family,
                 "bloodborne_visible_files": sum(bb_ext.get(e, 0) for e in suffixes),
                 "ds3_visible_files": sum(extensions.get(e, 0) for e in suffixes)}
                for family, suffixes in sorted(FAMILIES.items())
            ],
            "caution": "Archive contents excluded; file counts cannot prove compatible shaders or code",
        }
    return report

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ds3_dir", type=Path, help="local DS3 installation or Game folder")
    parser.add_argument("--bloodborne-report", type=Path, help="optional anonymous V146 JSON")
    parser.add_argument("--output", type=Path, help="JSON file outside DS3 Game folder")
    args = parser.parse_args(argv)
    try:
        root = game_root(args.ds3_dir)
        report = inventory(root, args.bloodborne_report)
        text = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.output:
            target = args.output.resolve(strict=False)
            if target.exists() or target == root or root in target.parents:
                raise InventoryError("refuse to overwrite or write inside DS3 installation")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as f:
                f.write(text)
            print("Saved anonymous DS3 metadata; no game data was opened or uploaded")
        else:
            sys.stdout.write(text)
        return 0
    except (InventoryError, OSError):
        print("DS3 reference inventory failed: unsupported or unsafe input", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
