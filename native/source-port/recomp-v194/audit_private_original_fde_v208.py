#!/usr/bin/env python3
"""V208 private Bloodborne PS4 ELF function metadata audit, no game bytes emitted.

Uses real PT_GNU_EH_FRAME FDE entries, checks pcrel starts, CIE backrefs,
non-overlapping function bounds and executable PT_LOAD containment.
A valid FDE is NOT a proof of compiled native function or game boot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
import tempfile

ELF_TYPE_PS4 = 0xFE10
PT_LOAD = 1
PT_GNU_EH_FRAME = 0x6474E550
MAX_FILE_SIZE = 512 * 1024 * 1024
MAX_FDES = 2_000_000


def inspect(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing/unsafe original private ELF")
    size = path.stat().st_size
    if not 4096 <= size <= MAX_FILE_SIZE:
        raise ValueError("private original ELF violates size bound")
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        if mm[:6] != b"\x7fELF\x02\x01":
            raise ValueError("expected little-endian ELF64")
        header = struct.unpack_from("<HHIQQQIHHHHHH", mm, 16)
        elf_type, machine, _, _, phoff, _, _, _, phsize, phcount, _, _, _ = header
        if elf_type != ELF_TYPE_PS4 or machine != 62 or phsize != 56 or (
            phcount == 0 or phcount > 64 or phoff + phcount * phsize > size
        ):
            raise ValueError("not a compatible PS4 x86-64 ELF header")
        phdrs = [struct.unpack_from("<IIQQQQQQ", mm, phoff + i * phsize)
                 for i in range(phcount)]
        if any(p[2] + p[5] > size for p in phdrs):
            raise ValueError("ELF program header points outside file")
        executables = [p for p in phdrs if p[0] == PT_LOAD and p[1] & 1]
        unwind = [p for p in phdrs if p[0] == PT_GNU_EH_FRAME]
        if len(executables) != 1 or len(unwind) != 1:
            raise ValueError("unexpected executable or unwind header segments")
        exe, eh = executables[0], unwind[0]
        eh_off, eh_addr, eh_size = eh[2], eh[3], eh[5]
        if eh_size < 12 or mm[eh_off:eh_off + 4] != b"\x01\x1b\x03\x3b":
            raise ValueError("unsupported .eh_frame_hdr pointer encodings")
        count = struct.unpack_from("<I", mm, eh_off + 8)[0]
        if count == 0 or count > MAX_FDES or 12 + count * 8 > eh_size:
            raise ValueError("invalid original ELF FDE table")
        exe_start, exe_end = exe[3], exe[3] + exe[6]
        previous_start = previous_end = -1
        cie_locations: set[int] = set()
        total_ranges = 0
        for index in range(count):
            loc_delta, fde_delta = struct.unpack_from("<ii", mm, eh_off + 12 + index * 8)
            start, fde = eh_addr + loc_delta, eh_addr + fde_delta
            fde_file = exe[2] + fde - exe[3]
            if not exe_start <= fde < exe_end or not 0 <= fde_file <= size - 16:
                raise ValueError("FDE descriptor outside original executable mapping")
            record_length, cie_back = struct.unpack_from("<II", mm, fde_file)
            code_delta, code_length = struct.unpack_from("<ii", mm, fde_file + 8)
            if (fde + 8 + code_delta != start or
                not 16 <= record_length <= 20_480 or
                fde_file + record_length + 4 > size or
                not 0 < cie_back <= fde + 4 or
                not 0 < code_length <= exe_end - start or
                not exe_start <= start < exe_end or
                start <= previous_start or start < previous_end):
                raise ValueError("FDE original function address/length mismatch or overlap")
            cie = fde + 4 - cie_back
            cie_file = exe[2] + cie - exe[3]
            if not 0 <= cie_file <= size - 8:
                raise ValueError("CIE backref outside original file")
            cie_len, cie_id = struct.unpack_from("<II", mm, cie_file)
            if cie_id != 0 or not 0 < cie_len < 20_480:
                raise ValueError("FDE backref does not point to original CIE")
            cie_locations.add(cie)
            total_ranges += code_length
            previous_start = start
            previous_end = start + code_length
        return {
            "format": "SHYT_PRIVATE_ORIGINAL_FDE_AUDIT_V208",
            "original_elf_sha256": hashlib.sha256(mm).hexdigest(),
            "input_bytes": size,
            "PS4_ELF64_x86_64": True,
            "executable_segment_file_bytes": exe[5],
            "reported_FDE_entries": count,
            "verified_unique_function_starts": count,
            "verified_CIE_references": count,
            "unique_CIE_records": len(cie_locations),
            "nonoverlapping_function_range_bytes": total_ranges,
            "invalid_FDE_entries": 0,
            "native_recompiled_functions_proven": 0,
            "native_game_boot_proven": False,
            "limitations": "FDE proves unwind-described original ranges, not complete function coverage or native Windows compilation."
        }


def selftest() -> None:
    blob = bytearray(0x3000)
    blob[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HHIQQQIHHHHHH", blob, 16,
                     ELF_TYPE_PS4, 62, 1, 0x200, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", blob, 64, PT_LOAD, 5, 0x1000,
                     0, 0, 0x2000, 0x2000, 0x1000)
    struct.pack_into("<IIQQQQQQ", blob, 120, PT_GNU_EH_FRAME, 4,
                     0x2800, 0x1800, 0, 0x100, 0x100, 4)
    struct.pack_into("<II", blob, 0x1600, 12, 0)  # artificial CIE
    struct.pack_into("<IIii", blob, 0x1620, 16, 0x24, -0x428, 10)
    struct.pack_into("<4B i I ii", blob, 0x2800, 1, 0x1b, 0x03, 0x3b,
                     -0x1204, 1, -0x1600, -0x11e0)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "artificial.bin"
        path.write_bytes(blob)
        out = inspect(path)
        assert out["reported_FDE_entries"] == 1
        assert out["unique_CIE_records"] == 1
        assert out["nonoverlapping_function_range_bytes"] == 10
        blob[0x1620 + 12] = 0  # zero the artificial function length
        path.write_bytes(blob)
        try:
            inspect(path)
        except ValueError:
            pass
        else:
            raise AssertionError("corrupt function length was accepted")
    print("SHYT_NATIVE_V208_PRIVATE_FDE_AUDIT_SELFTEST_PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="PRIVATE owner's eboot.bin-decrypted path")
    parser.add_argument("--output", type=Path, help="optional private JSON report path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        selftest()
    elif args.input:
        try:
            report = inspect(args.input)
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            if args.output.is_symlink():
                parser.error("report output cannot be a symbolic link")
            args.output.write_text(encoded, encoding="utf-8")
            print("SHYT_NATIVE_V208_PRIVATE_ELF_FDE_AUDIT_PASS")
        else:
            print(encoded)
    else:
        parser.error("specify --input or --self-test")
