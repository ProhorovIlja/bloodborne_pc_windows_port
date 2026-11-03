#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V18: private retail 1.09 ELF verification for opt-in BBHost NetSync.

For an OWNER-controlled Windows/WSL/Linux PC ONLY. No ELF is uploaded,
modified or copied. No private bytes, addresses, game paths or offsets are
printed. A successful exact hash + program-header check supports ONLY
the game's static original-file prologue, never live BBHost hook success.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import struct

ORIGINAL_109_SHA256="941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7"
TARGET_ELF_VA=0x017894E0  # YT v1.3.1 original NetSync send RVA
# First 6 bytes are public YT-source-attested. Remaining proposed bytes
# are a hypothesis, never considered verified without the original ELF.
CANDIDATE_PROLOGUE=bytes.fromhex("55 48 89 E5 41 57 41 56 41 55 41 54 53 48 83 EC")
MAX_INPUT_BYTES=256*1024*1024
MAX_PHDRS=128

class PrivateNetSyncRejected(ValueError):
    pass

def verified_original_image_v18(
    original:Path, *,
    expected_sha256:str=ORIGINAL_109_SHA256,
    target_va:int=TARGET_ELF_VA,
    candidate:bytes=CANDIDATE_PROLOGUE,
)->bool:
    # Overrides are permitted for invented fixture tests ONLY; the
    # production CLI has no option to override any locked values.
    original=original.absolute()
    chain=(original,*original.parents)
    if any(p.is_symlink() or (p/".git").exists() for p in chain):
        raise PrivateNetSyncRejected("original executable path unsafe")
    if not original.is_file() or not 64<=original.stat().st_size<=MAX_INPUT_BYTES:
        raise PrivateNetSyncRejected("original ELF missing or unsafe size")
    digest=hashlib.sha256()
    with original.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            digest.update(block)
    if digest.hexdigest()!=expected_sha256:
        raise PrivateNetSyncRejected("original 1.09 game image not authenticated")
    with original.open("rb") as f:
        header=f.read(64)
        if len(header)!=64 or header[:4]!=b"\x7fELF" or header[4:7]!=b"\x02\x01\x01":
            raise PrivateNetSyncRejected("not little-endian ELF64")
        if struct.unpack_from("<H",header,18)[0]!=0x3e:
            raise PrivateNetSyncRejected("not x86-64")
        phoff=struct.unpack_from("<Q",header,32)[0]
        phsize,phcount=struct.unpack_from("<HH",header,54)
        size=original.stat().st_size
        if phsize!=56 or not 1<=phcount<=MAX_PHDRS or phoff<64 or phoff+phsize*phcount>size:
            raise PrivateNetSyncRejected("invalid ELF program headers")
        if not 16<=len(candidate)<=64 or target_va<0:
            raise PrivateNetSyncRejected("invalid original instruction probe")
        f.seek(phoff)
        entries=f.read(phsize*phcount)
        mapped=[]
        for i in range(phcount):
            typ,flags,off,va,_,file_size,mem_size,_=struct.unpack_from(
                "<IIQQQQQQ",entries,i*phsize)
            if typ!=1 or (flags & 1)==0:
                continue
            if off+file_size>size or file_size>mem_size:
                raise PrivateNetSyncRejected("unsafe executable load segment")
            if va<=target_va and target_va+len(candidate)+1<=va+file_size:
                mapped.append(off+(target_va-va))
        if len(mapped)!=1:
            raise PrivateNetSyncRejected("missing or ambiguous executable mapping")
        f.seek(mapped[0])
        actual=f.read(len(candidate)+1)
    # Candidate prefix ends with the opcode for SUB RSP, imm8. The
    # final byte is the immediate. Only the actual game can confirm it.
    if actual[:len(candidate)]!=candidate or actual[16:17] not in (
        b"\x18",b"\x20",b"\x28",b"\x30",b"\x38",b"\x40",b"\x48",b"\x50",
        b"\x58",b"\x60",b"\x68",b"\x70",b"\x78",b"\x80",b"\x88",b"\x90"
    ):
        raise PrivateNetSyncRejected("NetSync prologue unsupported")
    return True

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--owner-decrypted-elf",type=Path,required=True)
    args=p.parse_args()
    try:
        assert verified_original_image_v18(args.owner_decrypted_elf)
    except (OSError,PrivateNetSyncRejected,ValueError):
        raise SystemExit("SHYT_V18_PRIVATE_NETSYNC_109_HOOK_REFUSED_NO_BYTES_EXPORTED") from None
    print("SHYT_V18_PRIVATE_ORIGINAL_109_NETSYNC_17_BYTE_PROLOGUE_VERIFIED_LOCAL_ONLY")
    print("NOT proof of a live game hook or seamless multiplayer.")

if __name__=="__main__":
    main()
