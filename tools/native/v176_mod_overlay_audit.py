#!/usr/bin/env python3
"""V176: local-only Bloodborne mod overlay inspection, never installs game files.

Safe metadata-only check for JSGME-style mods and separately staged CUSA-mods.
Default output contains no file or mod names, paths, hashes or game bytes.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import json
import os
import sys

SCHEMA = "SHYT_NATIVE_MOD_OVERLAY_PREFLIGHT_V176"
CONTENT = frozenset("action chr event facegen map menu movie msg mtd obj other param paramdef parts remo script sfx shader sound font".split())
IGNORED = frozenset({"!backup", "!instlogs", "_backup", "__macosx"})
BACKUPS = (".bak", ".orig", ".backup", ".disabled", ".tmp")
EXEC = frozenset({".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".py", ".scr", ".msi", ".com"})
MAX_MODS = 1024
MAX_FILES = 350000
MAX_PATHS = 64


class AuditError(ValueError):
    pass


def scan(root: Path) -> tuple[dict[str, int], dict]:
    if root.is_symlink() or not root.is_dir():
        raise AuditError("mod folder must be a regular directory")
    paths: dict[str, int] = {}
    counters = {"files": 0, "bytes": 0, "backups_ignored": 0,
                "symlinks_rejected": 0, "executable_candidates": 0,
                "noncontent_files": 0, "case_conflicts": 0}
    def onerror(_):
        raise AuditError("unreadable mod directory") from None
    for base, dirs, names in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        here = Path(base)
        for name in list(dirs):
            if (here / name).is_symlink():
                dirs.remove(name)
                counters["symlinks_rejected"] += 1
        for name in names:
            path = here / name
            if path.is_symlink():
                counters["symlinks_rejected"] += 1
                continue
            rel = path.relative_to(root).as_posix()
            if rel.casefold().endswith(BACKUPS):
                counters["backups_ignored"] += 1
                continue
            if not path.is_file():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                raise AuditError("unreadable mod file") from None
            counters["files"] += 1
            counters["bytes"] += size
            if counters["files"] > MAX_FILES:
                raise AuditError("mod file count exceeds safe bound")
            key = rel.casefold()
            if key in paths:
                counters["case_conflicts"] += 1
            else:
                paths[key] = size
            if path.suffix.casefold() in EXEC:
                counters["executable_candidates"] += 1
            if key.split("/", 1)[0] not in CONTENT:
                counters["noncontent_files"] += 1
    return paths, counters


def audit(mods_root: Path, *, existing_overlay: Path | None = None,
          include_paths: bool = False) -> dict:
    if mods_root.is_symlink():
        raise AuditError("symlinked mods root refused")
    root = mods_root.resolve(strict=True)
    if not root.is_dir():
        raise AuditError("mods root not a directory")
    children = list(root.iterdir())
    candidates = sorted((p for p in children if p.is_dir() and p.name.casefold() not in IGNORED),
                        key=lambda p: (p.name.casefold(), p.name))
    if len(candidates) > MAX_MODS:
        raise AuditError("too many mods")
    archives = sum(p.is_file() and p.suffix.casefold() in {".zip", ".7z", ".rar"}
                   for p in children)
    owners: dict[str, list[int]] = defaultdict(list)
    mods = []
    for index, mod in enumerate(candidates, 1):
        label = f"mod_{index:04d}"
        if mod.is_symlink():
            mods.append({"id": label, "status": "blocked_symlink", "files": 0})
            continue
        paths, counts = scan(mod)
        dirs = [p.name.casefold() for p in mod.iterdir() if p.is_dir()]
        if counts["symlinks_rejected"] or counts["executable_candidates"] or counts["case_conflicts"]:
            status = "blocked_unsafe_or_ambiguous"
        elif "dvdroot_ps4" in dirs or not any(d in CONTENT for d in dirs) or not paths or counts["noncontent_files"]:
            status = "needs_manual_structure_review"
        else:
            status = "ready_for_manual_compatibility_review"
        for rel in paths:
            owners[rel].append(index)
        entry = {"id": label, "status": status, **counts}
        if include_paths:
            entry.update(folder_name=mod.name,
                         relative_paths=sorted(paths)[:MAX_PATHS],
                         relative_paths_truncated=len(paths) > MAX_PATHS)
        mods.append(entry)
    collisions = {key: vals for key, vals in owners.items() if len(vals) > 1}
    overlap = 0
    if existing_overlay is not None:
        if existing_overlay.is_symlink():
            raise AuditError("symlinked overlay refused")
        over = existing_overlay.resolve(strict=True)
        scan_root = over / "dvdroot_ps4" if (over / "dvdroot_ps4").is_dir() else over
        if scan_root == root or root in scan_root.parents or scan_root in root.parents:
            raise AuditError("overlay must be separate from mods root")
        existing, _ = scan(scan_root)
        overlap = sum(rel in existing for rel in owners)
    report = {
        "schema": SCHEMA, "scope": "path-only preflight, NOT actual mod compatibility",
        "privacy": {"contents_read": False, "files_uploaded": False,
                    "absolute_paths_included": False, "relative_paths_opt_in": include_paths},
        "mod_directories": len(mods), "archives_uninspected": archives,
        "mods": mods, "conflicting_relative_paths": len(collisions),
        "existing_overlay_path_overrides": overlap,
        "blocked_mods": sum(m["status"].startswith("blocked") for m in mods),
        "manual_review_mods": sum(m["status"] == "needs_manual_structure_review" for m in mods),
        "ready_for_manual_review_mods": sum(m["status"] == "ready_for_manual_compatibility_review" for m in mods),
        "no_install_or_patch_performed": True,
    }
    if include_paths:
        report["collisions"] = [
            {"relative_path": rel, "mods": [f"mod_{n:04d}" for n in vals]}
            for rel, vals in sorted(collisions.items())[:MAX_PATHS]]
        report["collisions_truncated"] = len(collisions) > MAX_PATHS
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mods_root", type=Path)
    parser.add_argument("--existing-overlay", type=Path)
    parser.add_argument("--include-paths", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit(args.mods_root, existing_overlay=args.existing_overlay,
                       include_paths=args.include_paths)
        result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            target = args.output.resolve()
            roots = [args.mods_root.resolve()] + (
                [args.existing_overlay.resolve()] if args.existing_overlay else [])
            if any(target == p or p in target.parents for p in roots):
                raise AuditError("report must be outside game and mod directories")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
        return 0
    except (AuditError, OSError) as error:
        print("Mod audit failed: " + (str(error) if isinstance(error, AuditError)
                                    else "local filesystem error"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
