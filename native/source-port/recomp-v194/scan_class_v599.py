#!/usr/bin/env python3
"""Offline class-vtable candidates, only for the known CUSA03173 1.09 ELF."""
import argparse
import hashlib
import struct
from pathlib import Path


def scan(data):
    if hashlib.sha256(data).hexdigest() != "941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7":
        raise ValueError("expected the verified decrypted CUSA03173 1.09 ELF")
    rel = {addr: addend for addr, info, addend in struct.iter_unpack(
        "<QQq", memoryview(data)[0x53f4d30:0x5951e78]) if info == 8}

    def code(addr, length):
        if addr is None or not 0 <= addr <= 0x2bbe4a8 - length:
            return b""
        return data[addr + 0x4000:addr + 0x4000 + length]

    pairs = sorted(a - 0x10 for a, target in rel.items()
                   if code(target, 5) == bytes.fromhex("488b4740c3")
                   and code(rel.get(a + 8), 5) == bytes.fromhex("488b4748c3"))
    matches = []
    for table in pairs:
        keys = []
        for slot in range(0x20, 0x40, 8):
            target = rel.get(table + slot)
            op = code(target, 8)
            if len(op) != 8 or op[:3] != b"\x48\x8d\x05" or op[7] != 0xc3:
                break
            keys.append(target + 7 + struct.unpack_from("<i", op, 3)[0])
        if len(keys) == 4 and all(k == keys[0] - i for i, k in enumerate(keys)):
            matches.append((table, keys))
    return len(pairs), matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decrypted_elf", type=Path)
    parser.add_argument("--list", action="store_true", help="print candidate RVAs only")
    args = parser.parse_args()
    try:
        pairs, matches = scan(args.decrypted_elf.read_bytes())
    except (OSError, ValueError) as exc:
        parser.exit(2, f"scan refused: {exc}\n")
    print(f"name getter pairs: {pairs}; four consecutive key addresses: {len(matches)}")
    if args.list:
        for table, keys in matches:
            print("\t".join(f"{v:#x}" for v in [table, *keys]))


if __name__ == "__main__":
    main()
