#!/usr/bin/env python3
"""Assemble a non-released YT1.3 Windows kit from independently tested artifacts.

Only swap three actual native Protocol8 game executables compiled on Windows
from the original YT1.3 source with the source-verified V127 GPU extent fix.
All other files, V126 frozen BLauncher, vendor licenses, mods, shader resources,
and runtime DLLs MUST stay byte-identical to the pinned V126 portable kit.
This file does not download software, execute game payloads, or access Fornex.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile

PINNED_LAUNCHER_ZIP_SHA256 = (
    "d96c3a6884f12c2694544a6c814ce222e754f6b3da0d246037aaf65a0427c7dc"
)
SOURCE_YT130 = "0645740a33ae21c56df3b4a0d9777086dbca6053"
UPSTREAM_FIX = "https://github.com/lKaniel/bloodborne-server/pull/452"
EXE_MAP = {
    "bbport-windows/Bloodborne.exe": "bb-play.exe",
    "bbport-windows/bin/bb-probe.exe": "bb-probe.exe",
    "bbport-windows/bin/bb-gpu-capabilities.exe": "bb-gpu-capabilities.exe",
}
REQUIRED_UNCHANGED = {
    "bbport-windows/BLauncher.exe",
    "bbport-windows/licenses/PkgTool-LICENSE.txt",
    "bbport-windows/licenses/Intel-XeSS-LICENSE.txt",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pe_x64(path: Path) -> bytes:
    """Fail closed on missing, empty, non-x64, or corrupted PE files."""
    if not path.is_file() or path.is_symlink() or path.stat().st_size > (1 << 30):
        raise ValueError("Missing, linked or oversized compiled Windows EXE")
    content = path.read_bytes()
    if len(content) < 0x100 or content[:2] != b"MZ":
        raise ValueError("Compiled native Windows game is not an MZ executable")
    offset = struct.unpack_from("<I", content, 0x3c)[0]
    if offset < 0x40 or offset + 26 > len(content):
        raise ValueError("Corrupt PE header offset")
    if content[offset:offset + 4] != b"PE\0\0":
        raise ValueError("Missing PE signature")
    if struct.unpack_from("<H", content, offset + 4)[0] != 0x8664:
        raise ValueError("Not a native Windows x64 binary")
    return content


def check_names(archive: zipfile.ZipFile, strict: bool) -> set[str]:
    items = archive.infolist()
    if not items or len(items) > 18000 or (strict and len(items) < 100):
        raise ValueError("Unexpected source Windows archive entry count")
    seen = set()
    files = set()
    for item in items:
        n = item.filename
        if (not n.startswith("bbport-windows/") or not n.isascii()
                or chr(92) in n or ":" in n or chr(0) in n
                or ".." in PurePosixPath(n).parts):
            raise ValueError("Unsafe Windows archive member name")
        key = n.rstrip("/").casefold()
        if key in seen:
            raise ValueError("Windows case-insensitive archive collision")
        seen.add(key)
        if not item.is_dir():
            files.add(n)
    if not EXE_MAP.keys() <= files or (strict and not REQUIRED_UNCHANGED <= files):
        raise ValueError("Missing original game, BLauncher or essential vendor licenses")
    return files


def assemble(original: Path, compiled: Path, output: Path, report: Path,
             expected_sha: str = PINNED_LAUNCHER_ZIP_SHA256,
             *, strict: bool = True) -> dict:
    if output.resolve() == original.resolve():
        raise ValueError("Never modify the known-good input kit")
    source_hash = sha256(original.read_bytes())
    if source_hash != expected_sha:
        raise ValueError("Unverified V126 launcher-kit SHA256")
    compiled_files = {target: pe_x64(compiled / src) for target, src in EXE_MAP.items()}
    if output.exists():
        output.unlink()
    original_data = {}
    replaced = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(original) as before:
        files = check_names(before, strict)
        if before.testzip() is not None:
            raise ValueError("Bad CRC on original V126 kit")
        with zipfile.ZipFile(output, "w", allowZip64=True) as after:
            for info in before.infolist():
                # Retain original ZIP entry metadata; replace ONLY 3 binaries.
                old = before.read(info)
                if info.filename in compiled_files:
                    new = compiled_files[info.filename]
                    if old == new:
                        raise ValueError("Rebuilt V127 GPU binary is unchanged")
                    replaced[info.filename] = {"original_sha256": sha256(old),
                                               "v127_sha256": sha256(new)}
                    after.writestr(info, new)
                else:
                    if info.filename in files:
                        original_data[info.filename] = sha256(old)
                    after.writestr(info, old)
    with zipfile.ZipFile(output) as result:
        if check_names(result, strict) != files or result.testzip() is not None:
            raise ValueError("Repacked original Windows ZIP structure or CRC changed")
        for name, before_hash in original_data.items():
            if sha256(result.read(name)) != before_hash:
                raise ValueError("Non-GPU game files, BLauncher or licenses changed: " + name)
        if len(replaced) != 3:
            raise ValueError("Incomplete full native Protocol8 GPU EXE replacement")
    finished = {
        "pinned_original_yt130_source": SOURCE_YT130,
        "gpu_fix": UPSTREAM_FIX,
        "v126_launcher_original_kit_sha256": source_hash,
        "v127_integrated_internal_kit_sha256": sha256(output.read_bytes()),
        "changed_files": replaced,
        "all_other_file_bytes_verified_unchanged": True,
        "retail_game_assets_present": False,
        "gameplay_in_game_tested": False,
        "direct_p2p_verified": False,
        "production_ready": False,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(finished, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".zip.sha256").write_text(
        finished["v127_integrated_internal_kit_sha256"] + "  " + output.name + "\n",
        encoding="ascii")
    print("SHYT_V127_INTEGRATED_NATIVE_GPU_3_EXES_AND_V126_BLAUNCHER_BYTE_PRESERVATION_PASS")
    return finished


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--v126-kit", type=Path, required=True)
    p.add_argument("--compiled-gpu-exes", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    assemble(args.v126_kit, args.compiled_gpu_exes, args.output, args.report)
