"""Transactional installer and compatibility preflight for 3 audited Bloodborne 1.09 mod ZIPs.

This NEVER changes retail game files, the live server, save data or executable.
Only user-supplied archives with audited SHA256 are accepted; mod *assets* are
not included in this repository or portable release.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

KNOWN = {
    "55ce87acfbca9c5dab7500a73ca3c400c4e6f367c568e0655cdd7e6c5e2bb336":
        ("Jump on L3 Classic", "jump"),
    "ed504aa25cdff0384fa7d103140a332d49aaadf80034f6d242e1aa6487724b60":
        ("DollRebirth 1.0.2 bbport", "doll"),
    "d2708504cd50f1ce63bb2ed10044dd3ff7ca215fa4039d92e54ebea864dbfd90":
        ("MOAL 2.1.0 native", "moal"),
}
MAX_MEMBERS = 120
MAX_TOTAL = 32 * 1024 * 1024
MAX_FILE = 4 * 1024 * 1024


@dataclass(frozen=True)
class FileMapping:
    archive: Path
    member: str
    output: str
    source_hash: str


@dataclass
class Plan:
    mods: tuple[str, ...]
    files: tuple[FileMapping, ...]
    notes: tuple[str, ...]
    def summary(self):
        return {"mods": list(self.mods), "files": len(self.files),
                "notes": list(self.notes), "tested_online": False,
                "changes_game_files": False, "safe_for_live_server": True}


def _fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _inspect_archive(path: Path, jump_variant: str):
    digest = _fingerprint(path)
    known = KNOWN.get(digest)
    if known is None:
        raise ValueError("Unknown mod archive or newer version: its contents require a separate compatibility audit")
    name, kind = known
    if kind == "jump" and jump_variant not in ("jump_only", "enhanced"):
        raise ValueError("Jump variant must be jump_only or enhanced")
    files = []
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_MEMBERS or sum(e.file_size for e in entries) > MAX_TOTAL:
            raise ValueError("Unreasonable mod ZIP expansion or file count")
        seen = set()
        for info in entries:
            raw = info.filename
            rel = PurePosixPath(raw)
            if (not raw or raw.startswith("/") or "\\" in raw or ":" in raw or
                any(p in ("", ".", "..") for p in rel.parts) or
                len(raw) > 320 or info.flag_bits & 1):
                raise ValueError("Unsafe ZIP file name or encrypted member")
            normalized = raw.rstrip("/").casefold()
            if normalized in seen:
                raise ValueError("Duplicate Windows case-insensitive ZIP member")
            seen.add(normalized)
            mode = (info.external_attr >> 16) & 0o170000
            if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("ZIP symlinks, devices and special files are forbidden")
            if info.is_dir():
                continue
            if info.file_size > MAX_FILE:
                raise ValueError("Oversized individual mod file")
            target = None
            if kind == "jump":
                stem = ("Jump on L3 - Classic/" +
                        ("Enhanced/" if jump_variant == "enhanced" else "Jump only/"))
                if raw.startswith(stem):
                    tail = raw[len(stem):]
                    if tail == "dvdroot_ps4/action/script/c0000.hks":
                        target = "mods/JumpOnL3Classic/" + tail
                # Crucially never install Backup/ or both mutually exclusive variants.
            elif kind == "doll":
                if raw.startswith("mods/DollRebirth/dvdroot_ps4/"):
                    target = raw
                elif raw == "patches/DollRebirth.xml":
                    target = raw
            elif kind == "moal" and raw.startswith("MOAL/dvdroot_ps4/"):
                target = "mods/" + raw
            if target:
                if not target.startswith(("mods/", "patches/")):
                    raise ValueError("Unexpected mod destination")
                with archive.open(info) as src:
                    sha = hashlib.sha256()
                    count = 0
                    for block in iter(lambda: src.read(64 * 1024), b""):
                        count += len(block)
                        sha.update(block)
                    if count != info.file_size:
                        raise ValueError("Truncated archive member")
                files.append(FileMapping(path, raw, target, sha.hexdigest()))
        outputs = [f.output.casefold() for f in files]
        if len(outputs) != len(set(outputs)):
            raise ValueError("Archive maps multiple entries onto one game file")
    expected = {"jump": 1, "doll": 24, "moal": 31}[kind]
    if len(files) != expected:
        raise ValueError(f"{name}: unexpected mod file set ({len(files)}, expected {expected})")
    if kind == "doll" and not any(x.output == "patches/DollRebirth.xml" for x in files):
        raise ValueError("DollRebirth 1.09 executable patch missing")
    return kind, name, files


def _settings(path: Path):
    if not path.is_file():
        return {}
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError(f"Invalid config: {path.name}")
    return result


def _enabled_mod_files(mod_root: Path, config: Path):
    try:
        from scripts import mods
    except ModuleNotFoundError:
        # Also support "python scripts/community_mods.py" without the repo root
        # on sys.path (the Windows run.bat invokes scripts this way).
        import mods
    result = {}
    for name in mods.selected(mod_root, config):
        for relative, _ in mods.mod_files(mod_root / name):
            result.setdefault(relative.as_posix().casefold(), []).append(name)
    return result


def inspect(paths, data_dir: Path, jump_variant="jump_only"):
    base = Path(data_dir).resolve()
    archive_paths = [Path(p).resolve(strict=True) for p in paths]
    if not archive_paths:
        raise ValueError("Choose a Jump on L3, DollRebirth or MOAL ZIP")
    kinds, files, names = set(), [], []
    for path in archive_paths:
        kind, name, items = _inspect_archive(path, jump_variant)
        if kind in kinds:
            raise ValueError(f"Select one archive per mod: {name}")
        kinds.add(kind)
        names.append(name)
        files.extend(items)
    keys = [f.output.casefold() for f in files]
    if len(keys) != len(set(keys)):
        raise ValueError("Selected mod ZIPs overwrite one another")
    # Require the actual Doll dialogue, translations AND executable patch for MOAL
    # Rebirth. Missing either leaves an unusable lamp action.
    doll_present = "doll" in kinds or (base / "mods/DollRebirth/dvdroot_ps4/script/talk/m21_00_00_00.talkesdbnd.dcx").is_file()
    xml_present = "doll" in kinds or (base / "patches/DollRebirth.xml").is_file()
    if "moal" in kinds and not (doll_present and xml_present):
        raise ValueError("MOAL 2.1 requires DollRebirth (mod + DollRebirth.xml). Import both ZIPs together or install Doll first")
    if "moal" in kinds:
        mods_cfg = _settings(base / "mods.json")
        disabled = {str(x).casefold() for x in mods_cfg.get("disabled", [])}
        if "dollrebirth" in disabled:
            raise ValueError("DollRebirth is disabled in mods.json; MOAL Rebirth needs it enabled")
        patch_cfg = _settings(base / "patches.json")
        off = {str(x).casefold() for x in patch_cfg.get("disabled", [])}
        if "dollrebirth.xml/doll rebirth (respec)" in off:
            raise ValueError("DollRebirth XML patch is disabled in patches.json")
        ini = base / "bbport.ini"
        if ini.is_file():
            for line in ini.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                if "=" not in line or line.strip().startswith(("#",";")):
                    continue
                k, v = line.split("=",1)
                if k.strip().lower() in {"pc_enhanced_lamps","pc_boss_rematches","pc_two_invaders"} and v.strip().lower() not in ("0","false","off"):
                    raise ValueError(f"MOAL conflicts with enabled {k.strip()} in bbport.ini. Disable this game change first")
    installed = _enabled_mod_files(base / "mods", base / "mods.json")
    for file in files:
        if (base / file.output).exists() or (base / file.output).is_symlink():
            raise ValueError(f"Already installed, refusing overwrite: {file.output}")
        if file.output.startswith("mods/"):
            game_path = file.output.split("/", 2)[2].casefold()
            if game_path in installed:
                raise ValueError(f"Gameplay file conflict at {game_path}: {', '.join(installed[game_path])}")
    warnings = [
        "Only a Bloodborne 1.09 game dump is supported; archive authenticity is pinned by SHA256.",
        "Game archive and saves are never modified. Online sessions require identical gameplay mods/patches on peers.",
    ]
    if "jump" in kinds:
        warnings.append("Classic L3 requires a running jump; enhanced variant adds ladder drop and jump attack. This is not Modern neutral jump.")
    if "doll" in kinds:
        warnings.append("DollRebirth is a permanent respec action, not a reversible save edit. Back up the save before using Rebirth.")
    if "moal" in kinds:
        warnings.append("MOAL lamp interactions and travel are not verified in cross-map multiplayer; use only outside co-op until proven.")
    return Plan(tuple(names), tuple(files), tuple(warnings))


def install(plan: Plan, data_dir: Path):
    """All-or-rollback install: only new files, never overwrite existing mods/patches."""
    base = Path(data_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)
    roots = sorted({"/".join(f.output.split("/")[:2]) for f in plan.files})
    # Root for XML files is patches/DollRebirth.xml, not the whole patches directory.
    for root in roots:
        if (base / root).exists() or (base / root).is_symlink():
            raise ValueError(f"Install target already exists: {root}")
    with tempfile.TemporaryDirectory(dir=base, prefix=".sh-mod-install-") as temp:
        staging = Path(temp)
        for item in plan.files:
            obj = staging / item.output
            obj.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            with zipfile.ZipFile(item.archive) as archive, archive.open(item.member) as source, open(obj,"wb") as out:
                for chunk in iter(lambda: source.read(64 * 1024), b""):
                    out.write(chunk)
                    h.update(chunk)
            if h.hexdigest() != item.source_hash:
                raise ValueError("Archive changed during import; installation aborted")
        created = []
        try:
            for root in roots:
                dest = base / root
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() or dest.is_symlink():
                    raise ValueError(f"Concurrent modification: {root}")
                os.rename(staging / root, dest)
                created.append(dest)
        except BaseException:
            for obj in reversed(created):
                if obj.is_dir():
                    shutil.rmtree(obj)
                else:
                    obj.unlink()
            raise
    return {"installed": list(plan.mods), "new_files": len(plan.files),
            "original_game_untouched": True, "requires_restart": True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archives", nargs="+", type=Path)
    p.add_argument("--data-dir", type=Path, default=Path("."))
    p.add_argument("--jump-variant", choices=("jump_only","enhanced"), default="jump_only")
    p.add_argument("--install", action="store_true", help="Explicitly install after preflight; default is read-only")
    args = p.parse_args()
    try:
        plan = inspect(args.archives, args.data_dir, args.jump_variant)
        result = install(plan, args.data_dir) if args.install else plan.summary()
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        p.error(str(exc))

if __name__ == "__main__":
    main()
