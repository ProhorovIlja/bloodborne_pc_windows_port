#!/usr/bin/env python3
"""Read-only layout smoke test; not an asset decoder or runtime launcher."""
import argparse
import json
from pathlib import Path
import stat
import tempfile

# Sampling anchors, not a complete list of files needed to play.
ANCHORS = ("chr", "event", "map", "menu", "msg", "param", "shader", "sound")
CONSOLE_FILES = ("eboot.bin", "eboot.elf", "sce_module")


def kind(path):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return "absent"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    return "other"


def inspect(root):
    # This is a directory layout check, not a sandbox or a security guarantee
    # against concurrent filesystem changes, junctions or ancestor redirects.
    if kind(root) != "directory":
        raise ValueError("invalid title directory")
    asset_root = root / "dvdroot_ps4"
    if kind(asset_root) != "directory":
        raise ValueError("invalid asset directory")
    missing = [name for name in ANCHORS if kind(asset_root / name) != "directory"]
    return {
        "layout_ok": not missing,
        "missing_or_invalid_anchors": missing,
        "console_paths_present": [name for name in CONSOLE_FILES if kind(root / name) != "absent"],
        "asset_contents_validated": False,
        "runtime_independence_validated": False,
    }


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        asset_root = root / "dvdroot_ps4"
        asset_root.mkdir()
        for name in ANCHORS:
            (asset_root / name).mkdir()
        assert inspect(root)["layout_ok"]
        assert not inspect(root)["console_paths_present"]
        (root / "eboot.bin").write_bytes(b"not an executable")
        (root / "sce_module").mkdir()
        assert inspect(root)["layout_ok"]
        assert inspect(root)["console_paths_present"] == ["eboot.bin", "sce_module"]
        (asset_root / "sound").rmdir()
        (asset_root / "sound").touch()
        assert inspect(root)["missing_or_invalid_anchors"] == ["sound"]
        if hasattr(Path, "symlink_to"):
            try:
                (asset_root / "shader").rmdir()
                (asset_root / "shader").symlink_to(asset_root / "chr", target_is_directory=True)
            except OSError:  # Windows may deny fixture creation without Developer Mode.
                pass
            else:
                assert inspect(root)["missing_or_invalid_anchors"] == ["shader", "sound"]
    print("NATIVE_V428_ASSET_LAYOUT_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--title-root", type=Path)
    a = parser.parse_args()
    if a.self_test == (a.title_root is not None):
        parser.error("choose --self-test or --title-root")
    if a.self_test:
        self_test()
        return 0
    try:
        report = inspect(a.title_root)
    except (ValueError, OSError):
        print("title layout unavailable")
        return 2
    print(json.dumps(report, sort_keys=True))
    return int(not report["layout_ok"])


if __name__ == "__main__":
    raise SystemExit(main())
