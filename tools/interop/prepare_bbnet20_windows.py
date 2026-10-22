"""Prepare hash-verified deadinside bbnet20 sources for a separate Win64 DLL build.

This never builds a DLL, touches game files or modifies the production server.
Only two explicit Linux-to-Windows adaptations are applied to pinned sources.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

REVISION = "8185b88d80573fa300595d5c54450183b4109935"
FORMAT = "seamless-hunt-bbnet20-source-v1"
ROOTS = ("gpu/bbnet20/", "gpu/bbnet/bbnet.h", "gpu/third_party/httplib/")
GLUE = "gpu/bbnet20/bbnet_glue.cpp"
CMAKE = "gpu/bbnet20/CMakeLists.txt"
EXPORT = '#define BBNET_EXPORT extern "C" __attribute__((visibility("default")))'
LINK_OPTS = "target_link_options(bbnet20 PRIVATE -Wl,-Bsymbolic -Wl,--exclude-libs,ALL)"


def prepare(staged: Path, workspace: Path) -> dict:
    staged, workspace = staged.resolve(strict=True), workspace.resolve(strict=True)
    if not (workspace / "gpu/CMakeLists.txt").is_file():
        raise ValueError("workspace must be the native Windows port repository")
    inventory = staged / "PORT-SOURCE-MANIFEST.json"
    if not inventory.is_file() or inventory.is_symlink():
        raise ValueError("missing pinned source inventory")
    manifest = json.loads(inventory.read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT or manifest.get("revision") != REVISION:
        raise ValueError("unsupported or unreviewed upstream revision")
    if not isinstance(manifest.get("files"), list):
        raise ValueError("invalid source inventory")
    sources: dict[str, bytes] = {}
    for entry in manifest["files"]:
        if not isinstance(entry, dict):
            raise ValueError("bad inventory record")
        name = entry.get("path")
        if not isinstance(name, str):
            raise ValueError("bad source path")
        if not name.startswith(ROOTS):
            continue
        if ".." in name.split("/") or "\\" in name or name.startswith("/"):
            raise ValueError("unsafe upstream source path")
        source = staged.joinpath(*name.split("/"))
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(staged):
            raise ValueError(f"invalid upstream file: {name}")
        data = source.read_bytes()
        if (len(data) != entry.get("size") or
                hashlib.sha256(data).hexdigest() != entry.get("sha256")):
            raise ValueError(f"source SHA256 mismatch: {name}")
        if name in sources:
            raise ValueError("duplicate inventory entry")
        sources[name] = data
    expected = (GLUE, CMAKE, "gpu/bbnet/bbnet.h",
                "gpu/third_party/httplib/httplib.h", "gpu/third_party/httplib/LICENSE")
    if any(x not in sources for x in expected):
        raise ValueError("pinned source or third-party MIT license missing")
    if EXPORT.encode() not in sources[GLUE] or LINK_OPTS.encode() not in sources[CMAKE]:
        raise ValueError("upstream changed: explicitly review Windows adaptations")
    sources[GLUE] = sources[GLUE].replace(
        EXPORT.encode(),
        b'#ifdef _WIN32\n#define BBNET_EXPORT extern "C" __declspec(dllexport)\n'
        b'#else\n' + EXPORT.encode() + b'\n#endif')
    sources[CMAKE] = sources[CMAKE].replace(
        LINK_OPTS.encode(),
        b'if(NOT WIN32)\n    ' + LINK_OPTS.encode() + b'\nelse()\n'
        b'    target_compile_definitions(bbnet20 PRIVATE _CRT_SECURE_NO_WARNINGS)\n'
        b'    target_link_libraries(bbnet20 PRIVATE ws2_32 iphlpapi crypt32 bcrypt user32)\n'
        b'    set_target_properties(bbnet20 PROPERTIES PREFIX "" RUNTIME_OUTPUT_DIRECTORY "' +
        b'$' + b'{CMAKE_SOURCE_DIR}' + b'/../out/gpu")\n'
        b'endif()')
    destinations = (
        ("gpu/bbnet20", "gpu/bbnet20"),
        ("gpu/bbnet/bbnet.h", "gpu/bbnet/bbnet.h"),
        ("gpu/third_party/httplib", "gpu/third_party/httplib"),
    )
    for _, target in destinations:
        obj = workspace / target
        if obj.exists() or obj.is_symlink():
            raise ValueError(f"refusing to overwrite: {target}")
    for name in sources:
        target = workspace.joinpath(*name.split("/"))
        if not target.parent.resolve().is_relative_to(workspace):
            raise ValueError("destination escapes workspace")
    with tempfile.TemporaryDirectory(prefix=".bbnet20-source-", dir=workspace) as tmp:
        root = Path(tmp)
        for name, data in sorted(sources.items()):
            dest = root.joinpath(*name.split("/"))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        moved = []
        try:
            for origin, dest in destinations:
                target = workspace / dest
                target.parent.mkdir(parents=True, exist_ok=True)
                os.rename(root / origin, target)
                moved.append(target)
        except OSError:
            for dest in reversed(moved):
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            raise
    return {"source_revision": REVISION, "files_staged": len(sources),
            "adapted": [GLUE, CMAKE], "windows_online_dll_built": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.staged, args.workspace), sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
