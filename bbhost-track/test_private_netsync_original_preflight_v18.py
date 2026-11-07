#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V18: synthetic ELF segment-mapping fixtures, never any retail content."""
from __future__ import annotations
import hashlib
from pathlib import Path
import struct
import tempfile

from private_netsync_original_preflight_v18 import (
    CANDIDATE_PROLOGUE, PrivateNetSyncRejected,
    verified_original_image_v18
)

TARGET=0x2200

def elf(*, executable:bool=True, intact:bool=True, duplicate:bool=False)->bytes:
    result=bytearray(0x3000)
    result[:7]=b"\x7fELF\x02\x01\x01"
    struct.pack_into("<H",result,16,2)
    struct.pack_into("<H",result,18,0x3e)
    struct.pack_into("<Q",result,32,64)
    struct.pack_into("<HH",result,54,56,2 if duplicate else 1)
    seg=(1,5 if executable else 4,0x200,0x2000,0,0x1000,0x1000,0x1000)
    struct.pack_into("<IIQQQQQQ",result,64,*seg)
    if duplicate:
        struct.pack_into("<IIQQQQQQ",result,64+56,*seg)
    offset=0x200+(TARGET-0x2000)
    result[offset:offset+17]=CANDIDATE_PROLOGUE+b"\x28"
    if not intact:
        result[offset+8]=0xff
    return bytes(result)

def refused(call)->None:
    try:
        call()
    except PrivateNetSyncRejected:
        return
    raise AssertionError("private NetSync preflight silently accepted unsafe ELF")

def check()->None:
    with tempfile.TemporaryDirectory(prefix="shyt-v18-no-game-") as tmp:
        root=Path(tmp)
        file=root/"fictional-elf.bin"
        test=elf()
        file.write_bytes(test)
        digest=hashlib.sha256(test).hexdigest()
        assert verified_original_image_v18(file,expected_sha256=digest,
                                           target_va=TARGET)
        refused(lambda:verified_original_image_v18(file,target_va=TARGET))
        refused(lambda:verified_original_image_v18(
            file,expected_sha256="0"*64,target_va=TARGET))
        refused(lambda:verified_original_image_v18(
            file,expected_sha256=digest,target_va=TARGET+0x2000))
        for changes in (dict(executable=False),dict(intact=False),
                        dict(duplicate=True)):
            test=elf(**changes)
            file.write_bytes(test)
            digest=hashlib.sha256(test).hexdigest()
            refused(lambda:verified_original_image_v18(
                file,expected_sha256=digest,target_va=TARGET))
        file.write_bytes(elf())
        alias=root/"linked-original.bin"
        try:
            alias.symlink_to(file)
        except (OSError,NotImplementedError):
            pass
        else:
            refused(lambda:verified_original_image_v18(
                alias,expected_sha256=hashlib.sha256(elf()).hexdigest(),
                target_va=TARGET))
        (root/".git").mkdir()
        refused(lambda:verified_original_image_v18(
            file,expected_sha256=hashlib.sha256(elf()).hexdigest(),
            target_va=TARGET))

if __name__=="__main__":
    check()
    print("SHYT_V18_FAKE_ELF_PT_LOAD_PRIVATE_GAME_PROLOGUE_FAIL_CLOSED_PASS")
