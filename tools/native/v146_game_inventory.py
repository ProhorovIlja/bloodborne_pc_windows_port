#!/usr/bin/env python3
"""Read-only, local Bloodborne dump inventory for native Windows porting.

NO uploading, extracting, patching, decrypting or copying the game's assets.
The default JSON contains only aggregate sizes/counts and named required-file
presence. The operator explicitly opts in to relative paths and/or an
expensive normalized executable-image check. No absolute paths are emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import struct
from pathlib import Path
import sys

CRITICAL = ("eboot.bin", "sce_sys/param.sfo", "sce_module/libc.prx")
CONTENT_DIRS = ("dvdroot_ps4", "dvdroot_ps4/shader", "sce_module")
SCHEMA = "SHYT_NATIVE_ASSET_INVENTORY_V1"
# Reports must remain bounded even for accidentally selected drive roots.
MAX_FILES = 350_000
MAX_SFO_BYTES = 1024 * 1024


class InventoryError(ValueError):
    pass


def canonical_rel(relative: Path) -> str:
    return relative.as_posix()


def inventory(root: Path, *, include_paths: bool = False,
              verify_image: bool = False) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise InventoryError("select a game directory containing eboot.bin")
    # Require it at the root to prevent accidentally walking the whole drive.
    if not (root / "eboot.bin").is_file() or (root / "eboot.bin").is_symlink():
        raise InventoryError("missing regular eboot.bin in the selected game directory")

    extensions: Counter[str] = Counter()
    extension_bytes: Counter[str] = Counter()
    path_count = 0
    total_size = 0
    symlinks_skipped = 0
    case_conflicts = 0
    lowercase_seen = set()
    entries = []
    names = set()

    def walk_error(_error: OSError) -> None:
        raise InventoryError("some files could not be enumerated") from None

    for base, dirs, files in os.walk(root, topdown=True, followlinks=False,
                                     onerror=walk_error):
        base_path = Path(base)
        allowed_dirs = []
        for name in sorted(dirs):
            if (base_path / name).is_symlink():
                symlinks_skipped += 1
            else:
                allowed_dirs.append(name)
        dirs[:] = allowed_dirs
        for name in sorted(files):
            path = base_path / name
            if path.is_symlink():
                symlinks_skipped += 1
                continue
            if not path.is_file():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                raise InventoryError("a file became unreadable during inventory") from None
            rel = canonical_rel(path.relative_to(root))
            folded = rel.casefold()
            if folded in lowercase_seen:
                case_conflicts += 1
            lowercase_seen.add(folded)
            names.add(rel)
            suffix = Path(name).suffix.lower() or "(none)"
            extensions[suffix] += 1
            extension_bytes[suffix] += size
            path_count += 1
            total_size += size
            if path_count > MAX_FILES:
                raise InventoryError("more files than bounded inventory limit")
            if include_paths:
                entries.append({"path": rel, "bytes": size})
    dirs_present = {d: (root / Path(d)).is_dir() and not (root / Path(d)).is_symlink()
                    for d in CONTENT_DIRS}
    required = {name: name in names for name in CRITICAL}
    report: dict = {
        "schema": SCHEMA,
        "privacy": {
            "game_bytes_uploaded": False, "absolute_paths_included": False,
            "relative_paths_included": include_paths,
            "image_hash_checked": verify_image,
        },
        "files": path_count,
        "bytes": total_size,
        "extensions": [
            {"extension": ext, "files": extensions[ext], "bytes": extension_bytes[ext]}
            for ext in sorted(extensions)
        ],
        "required": required,
        "content_dirs": dirs_present,
        "symlinks_skipped": symlinks_skipped,
        "case_insensitive_path_collisions": case_conflicts,
    }
    if include_paths:
        report["relative_file_entries"] = entries
    if verify_image:
        # Reuse the exact existing original-port check for the normalized
        # loaded x86-64 image: SELF wrappers differ between legal dumps.
        scripts = Path(__file__).resolve().parents[2] / "scripts"
        sys.path.insert(0, str(scripts))
        import game_check
        from prepare import sfo

        if not required["sce_sys/param.sfo"]:
            raise InventoryError("cannot verify native image without sce_sys/param.sfo")
        if (root / "sce_sys/param.sfo").stat().st_size > MAX_SFO_BYTES:
            raise InventoryError("param.sfo is larger than safety limit")
        try:
            info = sfo((root / "sce_sys/param.sfo").read_bytes())
            image = game_check.image_sha256(root)
        except (OSError, ValueError, IndexError, KeyError, StopIteration,
                struct.error, UnicodeError, TypeError, OverflowError):
            raise InventoryError("native game metadata/executable verification failed") from None
        title_id = info.get("TITLE_ID")
        version = info.get("APP_VER") or info.get("VERSION")
        report["native_image_check"] = {
            "title_id": str(title_id) if title_id is not None else None,
            "declared_version": str(version) if version is not None else None,
            "retail_title_known": title_id in game_check.SUPPORTED_TITLES,
            "normalized_image_sha256": image,
            "known_clean_109": image == game_check.SUPPORTED_IMAGE,
            "known_60fps_patched": image == game_check.LANCE_60FPS_IMAGE,
        }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_dir", type=Path,
                        help="local directory containing your own eboot.bin")
    parser.add_argument("--output", type=Path,
                        help="write JSON outside the game folder (otherwise print stdout)")
    parser.add_argument("--include-paths", action="store_true",
                        help="opt in to file names relative to game root; NEVER embeds contents")
    parser.add_argument("--verify-image", action="store_true",
                        help="opt in to expensive loaded-image SHA256 and TITLE_ID/version check")
    args = parser.parse_args(argv)
    try:
        data = inventory(args.game_dir, include_paths=args.include_paths,
                         verify_image=args.verify_image)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            path = args.output.resolve()
            root = args.game_dir.resolve()
            if path == root or root in path.parents:
                raise InventoryError("report output must be outside the game directory")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print("Saved a metadata-only report; no game files copied or uploaded.")
        else:
            sys.stdout.write(text)
        return 0
    except (InventoryError, OSError) as exc:
        # Errors intentionally do not echo private absolute local paths.
        print("Inventory failed: " + (str(exc) if isinstance(exc, InventoryError)
                                     else "filesystem access error"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
