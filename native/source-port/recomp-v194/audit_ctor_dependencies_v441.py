#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Inspect direct transfers in one audited, contiguous retail constructor body.

GNU objdump is an offline decoder only. This is a linear body census, not a
reachability or closure proof. Supply a reviewed extent and initial table slot.
Only aggregate counts leave the tool; no disassembly or image data is printed.
"""
import argparse
import json
import mmap
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

from audit_first_load_v440 import from_first_load
from audit_private_ctor_closure_v410 import EH, PH

INSTR = re.compile(r"^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*(\S+)(?:\s+(.*))?$")
DEST = re.compile(r"(?:0x)?([0-9a-f]+)(?:\s+<[^>]+>)?")


def census(decoded, start, extent, target_kind):
    rows = {}
    cursor = start
    for line in decoded.splitlines():
        if not re.match(r"^\s*[0-9a-f]+:", line):
            continue
        match = INSTR.fullmatch(line)
        if not match:
            raise ValueError("unknown decoder row")
        address, data, op, arg = match.groups()
        pc, size = int(address, 16), len(data.split())
        if pc != cursor or not 1 <= size <= 15 or op.startswith((".", "(")) or op in ("rex", "lock", "rep", "repz", "repnz", "data16", "addr32", "bnd", "notrack"):
            raise ValueError("unsupported decode or prefix")
        cursor += size
        rows[pc] = (op, (arg or "").strip())
    if cursor != start + extent or not rows:
        raise ValueError("incorrect body coverage")
    out = dict(instructions=len(rows), native_calls=0, import_calls=0,
               indirect_calls=0, native_tails=0, import_tails=0,
               indirect_jumps=0, local_branches=0, returns=0,
               static_closure_proven=False, retail_execution_proven=False)
    for op, arg in rows.values():
        if op in ("ret", "retq"):
            out["returns"] += 1
        elif op.startswith(("call", "j", "loop")):
            call = op in ("call", "callq")
            jump = op in ("jmp", "jmpq")
            if arg.startswith("*") and (call or jump):
                out["indirect_calls" if call else "indirect_jumps"] += 1
                continue
            target = DEST.fullmatch(arg)
            if not target:
                raise ValueError("unknown transfer operand")
            target = int(target[1], 16)
            if start <= target < cursor:
                if target not in rows:
                    raise ValueError("transfer into instruction")
                out["local_branches"] += 1
            elif call or jump:
                kind = target_kind(target)
                if kind not in ("import", "native"):
                    raise ValueError("unclassified external target")
                out[kind + ("_calls" if call else "_tails")] += 1
            else:
                raise ValueError("conditional transfer outside audited extent")
    return out


def inspect(image, slot, ordinal, extent, objdump):
    targets, _ = from_first_load(image, slot)
    if not 1 <= ordinal <= len(targets) or not 1 <= extent <= 16384:
        raise ValueError("invalid body request")
    start = targets[ordinal - 1]
    head = EH.unpack_from(image)
    parts = [PH.unpack_from(image, head[5]+i*PH.size) for i in range(head[10])]
    dynamic = next(x for x in parts if x[0] == 2)
    blob = next(x for x in parts if x[0] == 0x61000000)
    tags = {}
    for t, v in struct.iter_unpack("<QQ", image[dynamic[2]:dynamic[2]+dynamic[5]]):
        if not t:
            break
        tags[t] = v
    jump_slots = set()
    for ptr, size in ((0x61000029, 0x6100002d), (0x6100002f, 0x61000031)):
        if ptr in tags:
            offset = blob[2] + tags[ptr]
            for address, info, _ in struct.iter_unpack("<QQq", image[offset:offset+tags[size]]):
                if info & 0xffffffff == 7:
                    jump_slots.add(address)

    def file_pos(address, length):
        for t, flags, offset, va, _, filesz, _, _ in parts:
            if t == 1 and flags & 1 and va <= address and address+length <= va+filesz:
                return offset + address - va
        raise ValueError("target not file-backed executable memory")

    def target_kind(address):
        pos = file_pos(address, 6)
        if image[pos:pos+2] != b"\xff\x25":
            return "native"
        displacement, = struct.unpack_from("<i", image, pos+2)
        return "import" if address+6+displacement in jump_slots else None

    pos = file_pos(start, extent)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "body.bin"
        source.write_bytes(image[pos:pos+extent])
        result = subprocess.run([objdump, "-D", "-b", "binary", "-m", "i386:x86-64",
                                 "--insn-width=16", f"--adjust-vma={start}", str(source)],
                                capture_output=True, check=True, timeout=10)
    return census(result.stdout.decode("ascii"), start, extent, target_kind)


def self_test():
    fixture = (" 10: e8 2b 00 00 00  call 0x40\n"
               " 15: ff d0  call *%rax\n"
               " 17: 75 f7  jne 0x10\n"
               " 19: e9 32 00 00 00  jmp 0x50\n")
    kinds = {0x40:"import", 0x50:"native"}
    result = census(fixture, 16, 14, kinds.get)
    assert all(result[k] == 1 for k in ("import_calls","indirect_calls","local_branches","native_tails"))
    for bad in (fixture.replace("0x10","0x11"), fixture.replace("0x50","0x99"),
                fixture.replace("jne","(bad)"), fixture.replace(" 17:"," 18:")):
        try:
            census(bad, 16, 14, kinds.get)
        except ValueError:
            continue
        raise AssertionError("invalid decode accepted")
    print("NATIVE_V441_CTOR_DEPENDENCIES_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--elf", type=Path)
    parser.add_argument("--first-load-slot", type=lambda value: int(value, 0))
    parser.add_argument("--ordinal", type=int, default=1)
    parser.add_argument("--extent", type=lambda value: int(value, 0))
    parser.add_argument("--objdump", default="objdump")
    args = parser.parse_args()
    if args.self_test and args.elf is None:
        self_test()
        return 0
    if args.self_test or any(x is None for x in (args.elf,args.first_load_slot,args.extent)):
        parser.error("specify a private ELF, first-load slot, and reviewed body extent")
    try:
        if args.elf.is_symlink() or not args.elf.is_file() or not 64 <= args.elf.stat().st_size <= 512 << 20:
            raise ValueError("unsafe input")
        with args.elf.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
            report = inspect(image,args.first_load_slot,args.ordinal,args.extent,args.objdump)
    except (ValueError, OSError, struct.error, subprocess.SubprocessError):
        print("private constructor dependency evidence refused", file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
