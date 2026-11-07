#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V10: game-free, network-free Windows modified BBHost packaging fixtures."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import tempfile

from assemble_modded_bbhost_v10 import (KIND, UPSTREAM, ModdedBundleRejected,
                                        stage_modified_v10)

COMMIT="3"*40
MARKER=("Upstream BBHost v0.2.24 verified against its signed release manifest.\n"
        "THIS IS AN EXPERIMENTAL ENGINE SELECTOR. YHARNAM TOGETHER "
        "SEAMLESS MULTIPLAYER IS NOT INTEGRATED INTO BBHOST YET.\n")

def pe(dll: bool, count: int) -> bytes:
    # Invented toy PE headers, NOT game data or a usable executable.
    image=bytearray(max(2048,count))
    image[:2]=b"MZ"
    struct.pack_into("<I",image,0x3c,0x80)
    image[0x80:0x84]=b"PE\x00\x00"
    struct.pack_into("<HH",image,0x84,0x8664,3)
    struct.pack_into("<H",image,0x80+22,0x2022 if dll else 0x0022)
    struct.pack_into("<H",image,0x80+24,0x20b)
    return bytes(image)

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def reject(fn) -> None:
    try:
        fn()
    except ModdedBundleRejected:
        pass
    else:
        raise AssertionError("Unsafe unsigned modified BBHost binary was accepted")

def case() -> None:
    with tempfile.TemporaryDirectory(prefix="shyt-v10-fictional-") as tmp:
        base=Path(tmp)
        launcher=base/"YT"
        hostdir=launcher/"bbhost"
        plugins=hostdir/"plugins"
        plugins.mkdir(parents=True)
        (launcher/"BLauncher.exe").write_bytes(pe(False,100000))
        (hostdir/"bbhost.exe").write_bytes(pe(False,130000))
        (hostdir/"SHYT-EXPERIMENTAL.txt").write_text(MARKER)
        (hostdir/"dxcompiler.dll").write_bytes(b"fictional-original-DXC-dependency")
        (plugins/"randomizer.dll").write_bytes(b"fictional-original-signed-upstream-plugin")
        candidate=base/"ci"
        candidate.mkdir()
        customhost=pe(False,150000)
        customplugin=pe(True,9500)
        (candidate/"bbhost.exe").write_bytes(customhost)
        (candidate/"shyt_bbhost_probe.dll").write_bytes(customplugin)
        info={
            "kind":KIND,
            "upstream_commit":UPSTREAM,
            "source_commit":COMMIT,
            "workflow_run_id":123456,
            "host_sha256":sha(customhost),
            "plugin_sha256":sha(customplugin)
        }
        manifest=candidate/"shyt-modified-build-v10.json"
        manifest.write_text(json.dumps(info))
        reject(lambda:stage_modified_v10(launcher,candidate,"deadbeef"))
        reject(lambda:stage_modified_v10(launcher,candidate,"4"*40))
        (candidate/"shyt_bbhost_probe.dll").write_bytes(customplugin+b"tamper")
        reject(lambda:stage_modified_v10(launcher,candidate,COMMIT))
        (candidate/"shyt_bbhost_probe.dll").write_bytes(customplugin)
        manifest.write_text(json.dumps({**info,"upstream_commit":"bad"}))
        reject(lambda:stage_modified_v10(launcher,candidate,COMMIT))
        manifest.write_text(json.dumps(info))
        stage_modified_v10(launcher,candidate,COMMIT)
        assert (hostdir/"bbhost.exe").read_bytes()==customhost
        assert (plugins/"shyt_bbhost_probe.dll").read_bytes()==customplugin
        assert (hostdir/"dxcompiler.dll").read_bytes()==b"fictional-original-DXC-dependency"
        assert (plugins/"randomizer.dll").is_file()
        assert (hostdir/"SHYT-V10-UNSIGNED-BUILD.json").is_file()
        assert "NOT SIGNED" in (hostdir/"SHYT-EXPERIMENTAL.txt").read_text()
        assert not (launcher/".bbhost-modified-v10.new").exists()
        assert not (launcher/".bbhost-official-v7.old").exists()
        assert not (launcher/"eboot.bin").exists()
        # Do not run a second install or silently repack an unsigned host.
        reject(lambda:stage_modified_v10(launcher,candidate,COMMIT))

if __name__=="__main__":
    case()
    print("SHYT_V10_INVENTED_PE_SHA256_TAMPER_AND_ATOMIC_BUNDLE_FIXTURES_PASS")
