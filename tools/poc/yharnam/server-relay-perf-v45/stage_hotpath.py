#!/usr/bin/env python3
"""Apply V45 C++ UDP hotpath optimization to the exact composed source tree.

This keeps the composed SHA-256 manifest truthful: a Windows/Ubuntu binary
must never be built from a post-manifest silently modified server_link.cpp.
Fail-closed if pinned source changed, hash drifted, or already patched.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

SOURCE = "server/src/server_link.cpp"
MANIFEST = "SEAMLESS-HUNT-COMPOSE-MANIFEST.json"
PIN = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"
IDENT = "V45 native shadNet UDP relay hotpath (no wire/protocol changes)"


def load_transform():
    script = Path(__file__).with_name("patch_server_hotpath.py")
    spec = importlib.util.spec_from_file_location("shyt_server_hotpath_v45", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.transform


def prepare(overlay: Path, transform=None) -> tuple[bytes, bytes]:
    root = overlay.resolve()
    manifest = root / MANIFEST
    target = root / SOURCE
    if not manifest.is_file() or not target.is_file():
        raise ValueError("missing composed server source or SHA-256 manifest")
    original_json = json.loads(manifest.read_text("utf-8"))
    if original_json.get("upstream_pin") != PIN or original_json.get("public_release_ready") is not False:
        raise ValueError("wrong Yharnam Together source pin or unsafe release declaration")
    expected_hash = original_json.get("sha256", {}).get(SOURCE)
    existing = target.read_bytes()
    if hashlib.sha256(existing).hexdigest() != expected_hash:
        raise ValueError("composed server source does not match the pre-patch SHA-256 manifest")
    if IDENT in original_json.get("applied", []):
        raise ValueError("V45 already staged in this source manifest")
    transformer = transform or load_transform()
    patched = transformer(existing.decode("utf-8")).encode("utf-8")
    if patched == existing:
        raise ValueError("optimizer did not change C++ server data path")
    actual_hash = hashlib.sha256(patched).hexdigest()
    original_json["sha256"][SOURCE] = actual_hash
    original_json["applied"].append(IDENT)
    original_json["native_udp_hotpath"] = {
        "enabled_in_build": True,
        "real_cpu_or_relay_bandwidth_improvement_verified": False,
        "game_protocol_changed": False,
        "old_sha256": expected_hash,
        "new_sha256": actual_hash,
    }
    # All source and manifest validations complete before creating files.
    new_manifest = (json.dumps(original_json, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return patched, new_manifest


def stage(overlay: Path) -> None:
    patched_source, patched_manifest = prepare(overlay)
    root = overlay.resolve()
    dest = root / SOURCE
    manifest = root / MANIFEST
    # Write both temporary files first. If the process dies between replacements,
    # the next invocation rejects mismatched bytes rather than compiling a lie.
    temp_code = dest.with_suffix(".cpp.pending-v45")
    temp_manifest = manifest.with_suffix(".json.pending-v45")
    try:
        temp_code.write_bytes(patched_source)
        temp_manifest.write_bytes(patched_manifest)
        temp_code.replace(dest)
        temp_manifest.replace(manifest)
    finally:
        temp_code.unlink(missing_ok=True)
        temp_manifest.unlink(missing_ok=True)
    recorded = json.loads(manifest.read_text("utf-8"))
    if hashlib.sha256(dest.read_bytes()).hexdigest() != recorded["sha256"][SOURCE]:
        raise ValueError("post-patch server source hash mismatch")
    print("SHYT_V45_ATOMIC_COMPOSE_SHA256_PASS", recorded["sha256"][SOURCE])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", required=True, type=Path)
    args = parser.parse_args()
    stage(args.overlay)


if __name__ == "__main__":
    main()
