#!/usr/bin/env python3
"""V209: private original ELF constant-return function AOT to no-ICF Win64 DLL.

Never publish original code, EBOOT, generated C or native objects. This tool
proves only constant-return leaf behavior, not full CPU/game boot equivalence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import mmap
from pathlib import Path
import struct
import subprocess
import tempfile

import audit_private_original_fde_v208 as fde


def classify(code: bytes) -> tuple[str, int] | None:
    if code == b"\x31\xc0\xc3":
        return ("zero", 0)
    if len(code) == 6 and code[0] == 0xB8 and code[-1] == 0xC3:
        return ("u32", struct.unpack_from("<I", code, 1)[0])
    if len(code) == 11 and code[:2] == b"\x48\xb8" and code[-1] == 0xC3:
        return ("u64", struct.unpack_from("<Q", code, 2)[0])
    return None


def collect(path: Path) -> list[tuple[int, int, str]]:
    fde.inspect(path)
    found = []
    with path.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        phoff = struct.unpack_from("<Q", mm, 32)[0]
        phnum = struct.unpack_from("<H", mm, 56)[0]
        segs = [struct.unpack_from("<IIQQQQQQ", mm, phoff + i * 56)
                for i in range(phnum)]
        exe = next(p for p in segs if p[0] == 1 and (p[1] & 1))
        eh = next(p for p in segs if p[0] == 0x6474E550)
        n = struct.unpack_from("<I", mm, eh[2] + 8)[0]
        for i in range(n):
            a, b = struct.unpack_from("<ii", mm, eh[2] + 12 + i * 8)
            addr, rec = eh[3] + a, exe[2] + eh[3] + b - exe[3]
            length = struct.unpack_from("<i", mm, rec + 12)[0]
            if length not in (3, 6, 11):
                continue
            offset = exe[2] + addr - exe[3]
            parsed = classify(mm[offset:offset + length])
            if parsed is not None:
                kind, value = parsed
                found.append((addr, value, kind))
    return found


def build(rows: list[tuple[int, int, str]], dest: Path) -> Path:
    if not rows or len(rows) > 100_000:
        raise ValueError("invalid or empty source cohort")
    dest = dest.resolve()
    if any((p / ".git").exists() for p in [dest, *dest.parents]):
        raise ValueError("private build output must NOT be inside Git")
    dest.mkdir(parents=True, exist_ok=True)
    source, obj, dll = (dest / "private_constants.c",
                        dest / "private_constants.obj",
                        dest / "private_constants.dll")
    with source.open("w", encoding="ascii") as out:
        out.write("/* PRIVATE converted constants; no full game runtime. */\n")
        for address, value, _ in rows:
            out.write("__declspec(dllexport) unsigned long long "
                      f"shyt_{address:016x}(void) {{return 0x{value:016x}ULL;}}\n")
    for stage, command in (
        ("compile", ["clang-cl", "/nologo", "/c", "/O2", "/GS-", "/Zl",
                     f"/Fo{obj}", str(source)]),
        ("link", ["lld-link", "/nologo", "/dll", "/noentry", "/nodefaultlib",
                  "/machine:x64", "/opt:noicf", f"/out:{dll}", str(obj)]),
    ):
        with (dest / f"{stage}.stderr").open("wb") as errors:
            result = subprocess.run(command, stdout=subprocess.DEVNULL,
                                    stderr=errors, timeout=180)
        if result.returncode:
            raise ValueError(f"Win64 {stage} failed; inspect PRIVATE stderr locally")
    return dll


def return_value(code: bytes) -> int | None:
    if code[:3] in (b"\x31\xc0\xc3", b"\x33\xc0\xc3"):
        return 0
    if code[:1] == b"\xb8" and code[5:6] == b"\xc3":
        return struct.unpack_from("<I", code, 1)[0]
    if code[:2] == b"\x48\xb8" and code[10:11] == b"\xc3":
        return struct.unpack_from("<Q", code, 2)[0]
    if code[:3] == b"\x48\xc7\xc0" and code[7:8] == b"\xc3":
        return struct.unpack_from("<i", code, 3)[0] & ((1 << 64) - 1)
    return None


def verify_pe(dll: Path, rows: list[tuple[int, int, str]]) -> dict:
    data = dll.read_bytes()
    if len(data) < 1024 or data[:2] != b"MZ":
        raise ValueError("no Windows PE output")
    off = struct.unpack_from("<I", data, 0x3c)[0]
    if data[off:off + 4] != b"PE\x00\x00":
        raise ValueError("PE signature invalid")
    coff, opt = off + 4, off + 24
    if (struct.unpack_from("<H", data, coff)[0],
        struct.unpack_from("<H", data, opt)[0]) != (0x8664, 0x20b):
        raise ValueError("not Windows x64 PE32+")
    n = struct.unpack_from("<H", data, coff + 2)[0]
    sec_start = opt + struct.unpack_from("<H", data, coff + 16)[0]
    sections = []
    for i in range(n):
        at = sec_start + 40 * i
        size, rva, raw_size, raw = struct.unpack_from("<IIII", data, at + 8)
        sections.append((rva, max(size, raw_size), raw))

    def file_offset(rva: int) -> int:
        for begin, span, raw in sections:
            if begin <= rva < begin + span:
                return raw + rva - begin
        raise ValueError("unmapped Windows export")

    if struct.unpack_from("<II", data, opt + 120) != (0, 0):
        raise ValueError("external PE imports forbidden for isolated cohort")
    exp = file_offset(struct.unpack_from("<I", data, opt + 112)[0])
    count, names = struct.unpack_from("<II", data, exp + 20)
    funcs, name_table, ordinals = struct.unpack_from("<III", data, exp + 28)
    if count != names or count != len(rows):
        raise ValueError("native exports missing")
    expected = {f"shyt_{address:016x}": value for address, value, _ in rows}
    if len(expected) != len(rows):
        raise ValueError("original functions must not share an address")
    seen_names: set[str] = set()
    seen_rvas: set[int] = set()
    for i in range(names):
        name_rva = struct.unpack_from("<I", data, file_offset(name_table) + 4 * i)[0]
        at = file_offset(name_rva)
        end = data.index(b"\x00", at, min(at + 40, len(data)))
        name = data[at:end].decode("ascii")
        if name not in expected or name in seen_names:
            raise ValueError("unknown or duplicate Windows export")
        ordinal = struct.unpack_from("<H", data, file_offset(ordinals) + 2 * i)[0]
        native_rva = struct.unpack_from("<I", data, file_offset(funcs) + 4 * ordinal)[0]
        if return_value(data[file_offset(native_rva):file_offset(native_rva) + 16]) != expected[name]:
            raise ValueError("native machine code differs from original return value")
        seen_names.add(name)
        seen_rvas.add(native_rva)
    if len(seen_rvas) != len(rows):
        raise ValueError("identical code folding destroys address-distinct original functions")
    return {"original_constant_functions": len(rows),
            "native_exported_functions": count,
            "distinct_PE_function_RVAs": len(seen_rvas),
            "return_value_mismatches": 0,
            "native_PE_imports": 0,
            "dll_size_bytes": len(data)}


def selftest() -> None:
    assert classify(b"\x31\xc0\xc3") == ("zero", 0)
    assert classify(b"\xb8\x01\x00\x00\x00\xc3") == ("u32", 1)
    assert classify(b"\x48\xb8" + b"\x09" * 8 + b"\xc3") == (
        "u64", 0x0909090909090909)
    assert classify(b"\xc3") is None
    with tempfile.TemporaryDirectory() as tmp:
        rows = [(0x200, 0, "zero"), (0x300, 1, "u32"),
                (0x400, 1, "u32"), (0x500, 0x123456789ABCDEF0, "u64")]
        assert verify_pe(build(rows, Path(tmp) / "fixture"), rows)[
            "distinct_PE_function_RVAs"] == 4
    print("SHYT_NATIVE_V209_WIN64_PRIVATE_CONSTANT_AOT_SELFTEST_PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        selftest()
    elif args.input and args.output_dir:
        try:
            rows = collect(args.input)
            dll = build(rows, args.output_dir)
            result = verify_pe(dll, rows)
            result["cohorts"] = dict(Counter(kind for _, _, kind in rows))
            result["native_game_boot_proven"] = False
            result["complete_CPU_semantics_proven"] = False
            (args.output_dir / "private_result.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print("SHYT_NATIVE_V209_PRIVATE_ORIGINAL_PE_AOT_PASS")
            print(json.dumps(result, separators=(",", ":")))
        except (ValueError, OSError, subprocess.TimeoutExpired, struct.error) as exc:
            parser.error(str(exc))
    else:
        parser.error("provide --input and --output-dir, or --self-test")
