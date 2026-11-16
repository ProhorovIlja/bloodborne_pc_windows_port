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


def bounded_span(image, offset, size):
    if not 0 <= offset <= len(image) or not 0 <= size <= len(image) - offset:
        raise ValueError("file span outside image")
    return image[offset:offset+size]


def jump_slot_set(image, dynamic, blob):
    tags = {}
    terminated = False
    relevant = {0x61000029, 0x6100002b, 0x6100002d,
                0x6100002f, 0x61000031, 0x61000033}
    for t, v in struct.iter_unpack("<QQ", bounded_span(image, dynamic[2], dynamic[5])):
        if not t:
            terminated = True
            break
        if t in relevant:
            if t in tags:
                raise ValueError("duplicate relocation tag")
            tags[t] = v
    if not terminated:
        raise ValueError("unterminated dynamic table")
    if tags.get(0x6100002b, 7) != 7 or tags.get(0x61000033, 24) != 24:
        raise ValueError("unsupported relocation layout")
    jump_slots = set()
    bounded_span(image, blob[2], blob[5])
    for ptr, size in ((0x61000029, 0x6100002d), (0x6100002f, 0x61000031)):
        if (ptr in tags) != (size in tags):
            raise ValueError("incomplete relocation table")
        if ptr in tags:
            rel, length = tags[ptr], tags[size]
            if rel > blob[5] or length > blob[5] - rel or length % 24:
                raise ValueError("relocation table outside SCE data or misaligned size")
            offset = blob[2] + rel
            for address, info, _ in struct.iter_unpack("<QQq", bounded_span(image, offset, length)):
                if info & 0xffffffff == 7:
                    jump_slots.add(address)
    return jump_slots


def body_plan(requests, count):
    if not 1 <= len(requests) <= 16:
        raise ValueError("batch must contain 1 to 16 bodies")
    seen = set()
    for ordinal, extent in requests:
        if not 1 <= ordinal <= count or not 1 <= extent <= 16384 or ordinal in seen:
            raise ValueError("invalid or duplicate body request")
        seen.add(ordinal)
    return sorted(requests)


def inspect_batch(image, slot, requests, objdump):
    targets, _ = from_first_load(image, slot)
    requests = body_plan(requests, len(targets))
    head = EH.unpack_from(image)
    parts = [PH.unpack_from(image, head[5]+i*PH.size) for i in range(head[10])]
    dynamic = [p for p in parts if p[0] == 2]
    blob = [p for p in parts if p[0] == 0x61000000]
    if len(dynamic) != 1 or len(blob) != 1:
        raise ValueError("ambiguous dynamic segments")
    jump_slots = jump_slot_set(image, dynamic[0], blob[0])

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

    reports = []
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "body.bin"
        for ordinal, extent in requests:
            start = targets[ordinal - 1]
            pos = file_pos(start, extent)
            source.write_bytes(bounded_span(image, pos, extent))
            result = subprocess.run([objdump, "-D", "-b", "binary", "-m", "i386:x86-64",
                                     "--insn-width=16", f"--adjust-vma={start}", str(source)],
                                    capture_output=True, check=True, timeout=10)
            reports.append(dict(ordinal=ordinal, **census(
                result.stdout.decode("ascii"), start, extent, target_kind)))
    return reports


def inspect(image, slot, ordinal, extent, objdump):
    report = inspect_batch(image, slot, [(ordinal, extent)], objdump)[0]
    del report["ordinal"]
    return report


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
    assert body_plan([(90, 12), (1, 16)], 90) == [(1, 16), (90, 12)]
    for invalid in ([], [(90, 1), (90, 2)], [(91, 1)], [(1, 16385)],
                    [(n, 1) for n in range(1, 18)]):
        try:
            body_plan(invalid, 90)
        except ValueError:
            continue
        raise AssertionError("invalid batch accepted")
    dynamic = (2, 0, 0, 0, 0, 48, 48, 8)
    blob = (0x61000000, 0, 48, 0, 0, 24, 24, 8)
    def data(*values):
        return struct.pack("<6QQQq", *values, 0x55, (1 << 32) | 7, 0)
    assert jump_slot_set(data(0x61000029, 0, 0x6100002d, 24, 0, 0), dynamic, blob) == {0x55}
    for invalid in ((0x61000029, 1, 0x6100002d, 24, 0, 0),
                    (0x61000029, 0, 0x6100002d, 23, 0, 0),
                    (0x61000029, 0, 0x61000029, 0, 0, 0),
                    (0x61000029, 0, 0x6100002d, 24, 1, 0),
                    (0x61000029, 0, 1, 0, 0, 0)):
        try:
            jump_slot_set(data(*invalid), dynamic, blob)
        except ValueError:
            continue
        raise AssertionError("invalid relocation metadata accepted")
    print("NATIVE_V441_CTOR_DEPENDENCIES_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--elf", type=Path)
    parser.add_argument("--first-load-slot", type=lambda value: int(value, 0))
    parser.add_argument("--ordinal", type=int)
    parser.add_argument("--body", nargs=2, action="append", type=lambda value: int(value, 0),
                        metavar=("ORDINAL", "EXTENT"), help="repeat for up to 16 reviewed bodies")
    parser.add_argument("--extent", type=lambda value: int(value, 0))
    parser.add_argument("--objdump", default="objdump")
    args = parser.parse_args()
    if args.self_test and args.elf is None:
        self_test()
        return 0
    if (args.self_test or args.elf is None or args.first_load_slot is None
            or (args.body and (args.extent is not None or args.ordinal is not None))
            or (not args.body and args.extent is None)):
        parser.error("specify a private ELF, first-load slot, and either --extent or repeated --body")
    try:
        if args.elf.is_symlink() or not args.elf.is_file() or not 64 <= args.elf.stat().st_size <= 512 << 20:
            raise ValueError("unsafe input")
        with args.elf.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
            if args.body:
                report = {"bodies": inspect_batch(image, args.first_load_slot, args.body, args.objdump),
                          "retail_execution_proven": False, "static_closure_proven": False}
            else:
                ordinal = 1 if args.ordinal is None else args.ordinal
                report = inspect(image, args.first_load_slot, ordinal, args.extent, args.objdump)
    except (ValueError, OSError, struct.error, subprocess.SubprocessError):
        print("private constructor dependency evidence refused", file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
