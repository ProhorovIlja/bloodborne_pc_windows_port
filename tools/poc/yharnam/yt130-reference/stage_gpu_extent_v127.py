#!/usr/bin/env python3
"""Backport only upstream merged YT #452 / shadPS4 #5524 texture extent fix.

Original v1.3 GPU cache uses C++20 lexicographic SubresourceExtent comparison.
An extra mip level cannot compensate for too few image layers (or vice versa).
Two sites must expand/recreate the cached image when either dimension is short.
This code stages ONLY on a pinned disposable native YT1.3 source checkout;
no retail assets, GPU drivers, saved games, networking or Fornex changes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
HEADER = "bbport/gpu/shadps4/video_core/texture_cache/types.h"
CPP = "bbport/gpu/shadps4/video_core/texture_cache/texture_cache.cpp"
HEADER_BLOB = "67e60702cfc533268adc58e7340a1bcef369e681"
CPP_BLOB = "127881844b5c6e71e4aa7d161a4ec8f01819570f"
OLD_STRUCT = """struct SubresourceExtent {
    u16 levels = 1;
    u16 layers = 1;

    auto operator<=>(const SubresourceExtent&) const = default;
};"""
NEW_STRUCT = """struct SubresourceExtent {
    u16 levels = 1;
    u16 layers = 1;

    auto operator<=>(const SubresourceExtent&) const = default;

    // Upstream YT #452 (shadPS4 #5524): both dimensions independently fit.
    // Lexicographic order incorrectly traded additional mips for layers.
    bool Contains(const SubresourceExtent& other) const noexcept {
        return levels >= other.levels && layers >= other.layers;
    }
};"""
OLD_RECREATE = "bool recreate = cache_image.info.resources < requested_info.resources;"
NEW_RECREATE = "bool recreate = !cache_image.info.resources.Contains(requested_info.resources);"
OLD_EXPAND = "image_info.resources > cache_image.info.resources) {"
NEW_EXPAND = "!cache_image.info.resources.Contains(image_info.resources)) {"


def rewrite(header: str, cpp: str) -> tuple[str, str]:
    for label, text, needle in (
        ("image extent struct", header, OLD_STRUCT),
        ("depth overlap recreate", cpp, OLD_RECREATE),
        ("image overlap expand", cpp, OLD_EXPAND),
    ):
        if text.count(needle) != 1:
            raise ValueError("Original GPU source drift: " + label)
    if "bool Contains(const SubresourceExtent& other)" in header:
        raise ValueError("Containment already staged")
    header = header.replace(OLD_STRUCT, NEW_STRUCT, 1)
    cpp = cpp.replace(OLD_RECREATE, NEW_RECREATE, 1).replace(OLD_EXPAND, NEW_EXPAND, 1)
    if "resources < requested_info.resources" in cpp or OLD_EXPAND in cpp:
        raise ValueError("Stale unsafe lexicographic comparison remains")
    return header, cpp


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Not official YT 1.3 pinned revision")
    for path, sha in ((HEADER, HEADER_BLOB), (CPP, CPP_BLOB)):
        if git(root, "rev-parse", "HEAD:" + path) != sha:
            raise ValueError("Original GPU source blob changed: " + path)
    h, cpp = root / HEADER, root / CPP
    hout, cout = rewrite(h.read_text(encoding="utf-8"), cpp.read_text(encoding="utf-8"))
    h.write_bytes(hout.encode("utf-8"))
    cpp.write_bytes(cout.encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V127_UPSTREAM_452_GPU_SUBRESOURCE_CONTAINMENT_STAGED_ONLY")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_pinned_original_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_pinned_original_yt130_checkout)
