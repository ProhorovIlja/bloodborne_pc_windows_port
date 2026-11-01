#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V232 read-only launcher preflight for actual published YT/BBPort mod loader.

Uses upstream bbport/scripts/mods.py discovery, selected() precedence and
mod_files() game layout, NOT a competing mod installer.  No game writes,
archive extraction, save changes, or network calls. Designed as a pre-launch
JSON source for the existing launcher UI, not yet wired into production.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import sys

MAX_MODS = 256
MAX_FILES = 160000
MAX_CONFLICTS = 4000
MAX_PATH = 260
GAMEPLAY_DIRS = frozenset({"param", "event", "script", "map"})
PROTECTED = frozenset({"eboot.bin", "sce_module", "sce_sys"})


def load_upstream(path: Path):
    if path.is_symlink() or not path.is_file() or path.name != "mods.py":
        raise ValueError("expected genuine upstream scripts/mods.py")
    spec = importlib.util.spec_from_file_location("yt_real_upstream_mods_v232", path)
    if not spec or not spec.loader:
        raise ValueError("cannot load original upstream mod file layout")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("selected", "mod_files", "content_root", "discover"):
        if not callable(getattr(module, name, None)):
            raise ValueError("missing expected upstream mod loader API")
    return module


def canonical(game_relative: Path) -> tuple[str, bool]:
    parts = game_relative.parts
    if not parts or any(x in ("", ".", "..") for x in parts):
        raise ValueError("unsafe game-relative mod path")
    if any(("\\" in x or ":" in x or "\x00" in x) for x in parts):
        raise ValueError("unsafe Windows mod path")
    if len(str(game_relative)) > MAX_PATH:
        raise ValueError("game-relative mod path exceeds Windows safety bound")
    folded = tuple(x.casefold() for x in parts)
    if folded[0] != "dvdroot_ps4" or len(folded) < 3:
        raise ValueError("unsafe root outside mounted game")
    if any(x in PROTECTED for x in folded):
        raise ValueError("executable/system replacement unsupported")
    return "/".join(folded), folded[1] in GAMEPLAY_DIRS


def inspect(upstream, mods_dir: Path, config: Path | None = None,
            base_overlay: Path | None = None) -> dict:
    if mods_dir.is_symlink() or not mods_dir.is_dir():
        raise ValueError("mod folder missing or symlinked")
    if config and (config.is_symlink() or
                   (config.exists() and not config.is_file())):
        raise ValueError("invalid selected mod profile")
    enabled = upstream.selected(mods_dir, config)
    if len(enabled) > MAX_MODS or len(set(x.casefold() for x in enabled)) != len(enabled):
        raise ValueError("too many enabled mods or duplicate casefold names")
    ordered: list[tuple[str, Path]] = []
    if base_overlay:
        if base_overlay.is_symlink() or not base_overlay.is_dir():
            raise ValueError("unsafe CUSA03173-mods path")
        if not upstream.content_root(base_overlay):
            raise ValueError("unrecognized CUSA03173-mods layout")
        ordered.append(("CUSA03173-mods [base overlay]", base_overlay))
    for name in enabled:
        directory = mods_dir / name
        if directory.is_symlink() or not directory.is_dir() or not directory.parent == mods_dir:
            raise ValueError("enabled mod directory invalid")
        ordered.append((name, directory))
    seen: dict[str, tuple[str, bool]] = {}
    rows: list[dict] = []
    replaced_mod_files = 0
    file_count = 0
    per_mod = defaultdict(int)
    for name, folder in ordered:
        current: set[str] = set()
        for game_path, source in upstream.mod_files(folder):
            if source.is_symlink() or not source.is_file():
                raise ValueError("upstream yielded an unsafe source file")
            key, gameplay = canonical(game_path)
            file_count += 1
            if file_count > MAX_FILES:
                raise ValueError("too many mod files for bounded preflight")
            if key in current:
                raise ValueError("case-insensitive duplicate target INSIDE one mod")
            current.add(key)
            per_mod[name] += 1
            previous = seen.get(key)
            if previous:
                prior_name, prior_gameplay = previous
                replaced_mod_files += 1
                if len(rows) < MAX_CONFLICTS:
                    rows.append({
                        "game_path": key,
                        "earlier": prior_name,
                        "winner": name,
                        "severity": "gameplay-critical" if gameplay or prior_gameplay else "overwrite",
                        "reason": "whole-file replacement; binary/DCX/BND contents are not merged"
                    })
            seen[key] = (name, gameplay)
    high = sum(x["severity"] == "gameplay-critical" for x in rows)
    conflicts_truncated = replaced_mod_files > len(rows)
    return {
        "format": "SHYT_V232_YT131_READONLY_MOD_PREFLIGHT",
        "upstream_mod_layout_used": True,
        "mod_precedence": [name for name, _ in ordered],
        "enabled_mod_count": len(enabled),
        "enumerated_game_files": file_count,
        "distinct_game_targets": len(seen),
        "file_replacements_between_mod_layers": replaced_mod_files,
        "reported_conflicts": rows,
        "reported_gameplay_critical_conflicts": high,
        "conflicts_truncated": conflicts_truncated,
        "per_mod_target_counts": dict(sorted(per_mod.items())),
        "has_unresolved_collisions": replaced_mod_files > 0,
        "mod_binary_compatibility_proven": False,
        "original_game_modified": False,
        "performance_improvement_proven": False,
        "server_compatibility_proven": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream-mods-script", required=True, type=Path)
    ap.add_argument("--mods-dir", required=True, type=Path)
    ap.add_argument("--profile", type=Path)
    ap.add_argument("--base-overlay", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        report = inspect(load_upstream(args.upstream_mods_script),
                         args.mods_dir, args.profile, args.base_overlay)
        encoded = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            if args.output.is_symlink() or not args.output.parent.is_dir():
                raise ValueError("unsafe output path")
            args.output.write_text(encoded + "\n", encoding="utf-8")
        else:
            print(encoded)
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"SHYT_V232_PREFLIGHT_FAIL: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
