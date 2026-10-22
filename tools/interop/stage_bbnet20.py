"""Stage pinned Linux bbnet20/BBSC sources for a separate Windows port.

No downloader, game files, executable DLL, networking or production changes.
The result is an auditable source tree, NOT a playable online integration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

UPSTREAM_COMMIT = "8185b88d80573fa300595d5c54450183b4109935"
REQUIRED = (
    "LICENSE", "docs/BBSC.md", "gpu/bbnet20/CMakeLists.txt",
    "gpu/bbnet20/SHADNET-PORT.md", "gpu/bbnet20/bbnet_glue.cpp",
    "gpu/bbnet20/bbsc/core/bloodborne_re.cpp", "gpu/bbnet/bbnet.h",
    "gpu/shim/bbport_guest_code_hooks.cpp",
    "gpu/shim/bbport_guest_code_hooks.h", "src/runtime_net.c",
)
STAGE_ROOTS = (
    "gpu/bbnet20", "gpu/bbnet/bbnet.h",
    "gpu/shim/bbport_guest_code_hooks.cpp",
    "gpu/shim/bbport_guest_code_hooks.h",
    "src/runtime_net.c", "docs/BBSC.md", "LICENSE",
)


def _git(source: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(source), *args],
                              check=True, capture_output=True, text=True,
                              timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("a complete, local Git checkout is required") from exc


def stage(source: Path, destination: Path, *, require_commit: str = UPSTREAM_COMMIT) -> dict:
    source = source.resolve(strict=True)
    destination = destination.absolute()
    if not source.is_dir() or len(require_commit) != 40:
        raise ValueError("invalid source tree or pin")
    actual = _git(source, "rev-parse", "HEAD").lower()
    if actual != require_commit:
        raise ValueError(f"unreviewed upstream revision: {actual}")
    if _git(source, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("upstream tracked files have local edits")
    if destination.exists() or destination.is_symlink():
        raise ValueError("destination already exists; previous snapshot preserved")
    if destination == source or source in destination.parents:
        raise ValueError("destination may not be inside source")
    for rel in REQUIRED:
        src = source / rel
        if not src.is_file() or src.is_symlink():
            raise ValueError(f"required upstream source missing or linked: {rel}")
    files = {}
    for rel in STAGE_ROOTS:
        src = source / rel
        if src.is_symlink() or not src.exists():
            raise ValueError(f"missing or linked source subtree: {rel}")
        iterator = (src,) if src.is_file() else src.rglob("*")
        for item in iterator:
            if item.is_symlink():
                raise ValueError(f"upstream symlink refused: {item}")
            if item.is_file():
                files[item.relative_to(source).as_posix()] = item
            elif not item.is_dir():
                raise ValueError(f"nonregular upstream file: {item}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".bbnet20-", dir=destination.parent) as tmp:
        root = Path(tmp)
        entries = []
        for name, item in sorted(files.items()):
            dest = root.joinpath(*name.split("/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = item.read_bytes()
            dest.write_bytes(data)
            entries.append({"path": name, "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
        manifest = {"format": "seamless-hunt-bbnet20-source-v1",
                    "upstream": "deadinside28/bloodborne_pc", "revision": actual,
                    "purpose": "audit/Windows adaptation, not playable online",
                    "files": entries}
        (root / "PORT-SOURCE-MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(root, destination)
    return {"commit": actual, "files": len(entries), "destination": str(destination)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(stage(args.from_checkout, args.output), sort_keys=True))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
