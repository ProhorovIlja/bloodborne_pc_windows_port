#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Public CI exercises ONLY fake ELF bytes; user's 1.09 assets stay private."""
from pathlib import Path
import tempfile
from check_owner_bbhost_109_v1 import compatible

def main()->None:
    with tempfile.TemporaryDirectory(prefix="shyt-bbhost-fake-game-") as directory:
        root=Path(directory)
        elf=root/"synthetic.elf"
        elf.write_bytes(b"\x7fELF\x02"+b"test-not-real-game"*8)
        assert compatible(elf)==(True,False)
        not_elf=root/"unrelated.bin"
        not_elf.write_bytes(b"NOT-AN-ELF"+b"B"*120)
        assert compatible(not_elf)==(False,False)
        link=root/"linked.elf"
        try:
            link.symlink_to(elf)
        except (OSError,NotImplementedError):
            pass
        else:
            try:
                compatible(link)
            except ValueError:
                pass
            else:
                raise AssertionError("symlink allowed")
        tiny=root/"tiny.elf"
        tiny.write_bytes(b"\x7fELF\x02")
        try:
            compatible(tiny)
        except ValueError:
            pass
        else:
            raise AssertionError("truncated game accepted")
    print("SHYT_BBHOST_V1_OWNER_PRIVATE_IMAGE_GATE_FAKE_INPUTS_PASS")

if __name__=="__main__":
    main()
