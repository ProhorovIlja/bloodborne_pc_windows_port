#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V1: owner-local BBHost 1.09 image compatibility gate, no file disclosure.

BBHost v0.2.24 accepts ONLY the exact original decrypted 1.09 ELF SHA.
The user's CUSA03173 GOTY dump must be checked, NOT assumed compatible
because it shares the 01.09 label with the CUSA00900 example.
Run on the owner's private machine. Never attach an eboot to GitHub CI.
Outputs booleans only (no filename, path, size, hash or bytes).
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import stat

PINNED_BBHOST_109 = "941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7"
MAX_ORIGINAL_ELF = 256 * 1024 * 1024
CHUNK = 1024 * 1024

def compatible(path:Path)->tuple[bool,bool]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("unsafe private game input")
    # No source checkout, repository nor user content can be copied
    # to the public CI or staged under the code tree by accident.
    root=Path(__file__).resolve().parents[1]
    p=path.resolve(strict=True)
    if p==root or root in p.parents:
        raise ValueError("refusing repository-local game binaries")
    info=p.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size<=64 or info.st_size>MAX_ORIGINAL_ELF:
        raise ValueError("not a bounded original 1.09 ELF")
    digest=hashlib.sha256()
    signature=b""
    with p.open("rb") as source:
        while True:
            block=source.read(CHUNK)
            if not block:
                break
            if not signature:
                signature=block[:5]
            digest.update(block)
    elf64=signature==b"\x7fELF\x02"
    return elf64,elf64 and digest.hexdigest()==PINNED_BBHOST_109

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--owner-private-eboot",required=True,type=Path)
    args=parser.parse_args()
    try:
        elf,match=compatible(args.owner_private_eboot)
    except (OSError,ValueError):
        print("SHYT_BBHOST_V1_EBOOT_ELF64=False MATCHES_EXACT_109=False")
        raise SystemExit(2) from None
    print(f"SHYT_BBHOST_V1_EBOOT_ELF64={elf} MATCHES_EXACT_109={match}")
    if not match:
        raise SystemExit(3)

if __name__=="__main__":
    main()
