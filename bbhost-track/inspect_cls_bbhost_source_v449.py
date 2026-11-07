#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V449: bounded release-source build-graph reconnaissance, never game dumps.

Inspects exact public CLS v1.4.0 BBHost SOURCE zip. Emits only structural
metadata and bounded CMake build lines. It never executes archive contents.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

EXPECTED_SHA = "7c00d46f01b67ff1cf12cef346c245960b627141a9c1047d00e2ceadd167ca04"
MAX_ZIP = 32*1024*1024
MAX_ENTRIES = 40000
MAX_TEXT = 150*1024

def audit(archive: Path) -> dict:
    if not archive.is_file() or archive.is_symlink() or archive.stat().st_size > MAX_ZIP:
        raise ValueError("not a bounded regular source archive")
    with archive.open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != EXPECTED_SHA:
            raise ValueError("release checksum drift")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not members or len(members) > MAX_ENTRIES:
            raise ValueError("member count")
        names: set[str] = set()
        clean: list[str] = []
        total = 0
        for it in members:
            n=it.filename.replace("\\", "/")
            p=PurePosixPath(n)
            if (not n.isascii() or n.startswith("/") or ".." in p.parts
                or ":" in n or not n or (it.external_attr>>16)&0o170000 in (0o120000,0o060000)):
                raise ValueError("unsafe source path")
            if it.is_dir():
                continue
            if n in names:
                raise ValueError("duplicate source path")
            names.add(n)
            clean.append(n)
            total+=it.file_size
            if total > 1_000_000_000:
                raise ValueError("expanded source archive too large")
            if n.lower().endswith(("eboot.bin",".pkg",".sfo",".self")):
                raise ValueError("game content not source code")
        roots=sorted({PurePosixPath(x).parts[0] for x in clean})
        markers=[]
        for n in sorted(clean):
            low=n.lower()
            if any(token in low for token in ("yt_host", "yt_ui", "bbsc_yt", "bbcoop", "bbnet", "yt_nids", "cmakelists", "ci_build", "readme")):
                if len(markers) < 160:
                    markers.append({"path":n,"size":z.getinfo(n).file_size})
        cmake=[]
        for n in sorted(clean):
            if len(cmake)>=24: break
            if not (n.lower().endswith("cmakelists.txt") or n.lower().endswith(".cmake")):continue
            it=z.getinfo(n)
            if not 0<it.file_size<=MAX_TEXT:continue
            try:s=z.read(it).decode("utf-8")
            except UnicodeError:continue
            lines=[]
            for i,raw in enumerate(s.splitlines(),1):
                if re.search(r"(?i)\b(yt|bbcoop|bbnet|bbport|bbhost|SDL|Vulkan)\b|add_subdirectory\(|target_link_libraries\(",raw):
                    lines.append({"line":i,"text":raw[:160]})
                if len(lines)>=20:break
            if lines:cmake.append({"path":n,"lines":lines})
        return {"schema":"SHYT-V449-CLS-BBHOST-PUBLIC-SOURCE-GRAPH",
                "release_sha256":EXPECTED_SHA,"compressed_bytes":archive.stat().st_size,
                "members":len(clean),"expanded_bytes":total,"roots":roots[:25],
                "interesting_paths":markers, "cmake_edges":cmake,
                "proof_only":"public-source-layout-not-game-boot-or-ABI-validation"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    out=audit(a.archive)
    a.report.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("SHYT_V449_SOURCE_LAYOUT_PIN_PASS")
    print("V449_MEMBER_COUNT",out["members"],"ROOTS",json.dumps(out["roots"]))
    print("V449_BUILD_FILES",json.dumps([x["path"] for x in out["cmake_edges"]]))
    print("V449_KEY_FILES",json.dumps([x["path"] for x in out["interesting_paths"][:60]]))
    for x in out["cmake_edges"][:8]:
        selected=[v for v in x["lines"] if re.search(r"(?i)yt|bbcoop|bbnet|bbport|bbhost",v["text"])]
        if selected: print("V449_BUILD_EDGE",x["path"],json.dumps(selected[:6]))
    print("SHYT_V449_RELEASE_SOURCE_BUILD_GRAPH_REPORT_ONLY")

if __name__=="__main__":
    main()
