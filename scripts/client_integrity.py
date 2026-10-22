"""Read-only integrity diagnostics for an EXTRACTED Seamless Hunt Windows dev kit.

Checks the immutable files against the MANIFEST.json bundled in the same
verified-when-packed ZIP. Does not download, install, repair, delete, execute or
open game saves. It explicitly does not prove authenticity: a modified local
manifest can be forged. Future auto-update requires a *signed* release root.

The checker is shipped in scripts/, uses only Python stdlib, and can run while
the normal launcher is open. File sizes and hashes are compared on disk without
loading binaries into RAM. Unknown third-party mods / user data are never scanned.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re

FORMAT = "seamless-hunt-native-windows-dev-v2"
MAX_MANIFEST = 12 * 1024 * 1024
MAX_ITEMS = 50000
MAX_SINGLE_FILE = 512 * 1024 * 1024
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
LEGAL_ROOTS = frozenset({
    "out", "python", "scripts", "patches", "launcher", "licenses",
    "docs", "tools", "VERSION", "LICENSE", "README.md", "README.ru.md",
    "CHANGELOG.md", "launch_gui.bat", "run.bat", "launcher.py",
})
FORBIDDEN_PARTS = frozenset({
    "user", "savedata", "save", "mods", ".git", ".github",
    "site-packages", "secrets", "__pycache__", "logs",
})
REQUIRED = frozenset({
    "launcher.py", "run.bat", "launch_gui.bat", "out/bbport.exe",
    "python/python.exe", "python/pythonw.exe", "python/python312.dll",
})


@dataclass(frozen=True)
class Check:
    path: str
    status: str  # ok, missing, mismatch, unsafe
    critical: bool


@dataclass(frozen=True)
class Integrity:
    revision: str
    checked: int
    critical_errors: int
    optional_changes: int
    items: tuple[Check, ...]

    def as_dict(self):
        return {**asdict(self), "source_authenticity_verified": False,
                "save_files_examined": False}


def _valid_rel(name: str) -> bool:
    if not isinstance(name, str) or not name or len(name) > 240:
        return False
    if "\\" in name or ":" in name or name[0] == "/":
        return False
    parts = name.split("/")
    if (parts[0] not in LEGAL_ROOTS
            or any(p in ("", ".", "..") or p in FORBIDDEN_PARTS
                   or p.endswith((" ", ".")) or any(ord(ch) < 32 for ch in p)
                   for p in parts)):
        return False
    if parts[0] == "out" and len(parts) > 2 and parts[1] != "licenses" and name != "out/gpu/bbnet20.dll":
        return False
    return True


def _critical(name: str) -> bool:
    return (name in REQUIRED or name.startswith(("out/", "python/", "scripts/"))
            or name in ("VERSION", "launcher.py", "run.bat", "launch_gui.bat"))


def _read_manifest(root: Path) -> tuple[str, list[tuple[str, int, str]]]:
    file = root / "MANIFEST.json"
    if file.is_symlink() or not file.is_file():
        raise ValueError("No installed build manifest; cannot verify extracted client")
    size = file.stat().st_size
    if size < 40 or size > MAX_MANIFEST:
        raise ValueError("Installed manifest exceeds allowed size")
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, ValueError) as ex:
        raise ValueError("Installed manifest invalid") from ex
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("Not a recognized Seamless Hunt Windows dev manifest")
    rev = data.get("source_commit")
    if not isinstance(rev, str) or not COMMIT_RE.fullmatch(rev):
        raise ValueError("Missing or invalid source revision")
    entries = data.get("files")
    if not isinstance(entries, list) or len(entries) < len(REQUIRED) or len(entries) > MAX_ITEMS:
        raise ValueError("Unexpected build-file inventory")
    seen, files = set(), []
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("Invalid inventory entry")
        name, size, digest = item.get("path"), item.get("bytes"), item.get("sha256")
        if not _valid_rel(name):
            raise ValueError("Unsafe manifest path")
        key = name.casefold()
        if key in seen:
            raise ValueError("Duplicate or case-colliding manifest path")
        seen.add(key)
        if (type(size) is not int or not 0 <= size <= MAX_SINGLE_FILE
                or not isinstance(digest, str) or not SHA_RE.fullmatch(digest)):
            raise ValueError("Invalid build-file size or hash")
        files.append((name, size, digest))
    if not REQUIRED <= {name for name, _, _ in files}:
        raise ValueError("Core launcher/runtime files absent from manifest")
    return rev, files


def _hash_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_installed(root: Path) -> Integrity:
    """Validate only packaged, explicitly inventoried files. Never scan mod/save trees."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("No extracted client directory")
    revision, entries = _read_manifest(root)
    findings = []
    for name, size, digest in entries:
        critical = _critical(name)
        path = root
        # Reject symlink/junction ancestors; no escape to user data or network mounts.
        unsafe = False
        for component in name.split("/"):
            path = path / component
            if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                unsafe = True
                break
        if unsafe:
            findings.append(Check(name, "unsafe", critical))
            continue
        try:
            if not path.is_file():
                findings.append(Check(name, "missing", critical))
                continue
            first = path.stat()
            if first.st_size != size:
                findings.append(Check(name, "mismatch", critical))
                continue
            actual_hash = _hash_file(path)
            last = path.stat()
            if ((first.st_dev, first.st_ino, first.st_size, first.st_mtime_ns)
                    != (last.st_dev, last.st_ino, last.st_size, last.st_mtime_ns)):
                findings.append(Check(name, "mismatch", critical))
                continue
            findings.append(Check(name, "ok" if actual_hash == digest else "mismatch", critical))
        except OSError:
            findings.append(Check(name, "missing", critical))
    return Integrity(
        revision=revision,
        checked=len(findings),
        critical_errors=sum(x.status != "ok" and x.critical for x in findings),
        optional_changes=sum(x.status != "ok" and not x.critical for x in findings),
        items=tuple(findings),
    )


def summary(report: Integrity) -> str:
    if report.critical_errors:
        heading = f"{report.critical_errors} CORE CLIENT FILE(S) NEED ATTENTION"
    elif report.optional_changes:
        heading = "Core files match; optional files changed or missing"
    else:
        heading = "Installed client files match the bundled manifest"
    changed = [f"{'CRITICAL' if item.critical else 'Optional'}: "
               f"{item.path} ({item.status})" for item in report.items if item.status != "ok"]
    return ("\n".join([
        heading, f"Revision: {report.revision}",
        f"Checked: {report.checked}",
        f"Core mismatches: {report.critical_errors}",
        f"Optional differences: {report.optional_changes}",
        *changed[:30],
        "" if len(changed) <= 30 else f"... {len(changed)-30} more differing files",
        "Local checksums detect damage, NOT forged packages or publisher identity.",
        "Game files, saves, mods, account data and user settings were not examined.",
    ])).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-dir", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        info = verify_installed(args.client_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(info.as_dict(), indent=2) if args.json else summary(info))
    return 0 if not info.critical_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
