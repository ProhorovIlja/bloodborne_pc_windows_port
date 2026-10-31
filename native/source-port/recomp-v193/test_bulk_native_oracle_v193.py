"""Synthetic-only native execution oracle for ALL ten V193 leaf grammars.

This fixture is invented, not extracted from a game or private manifest.
"""
import ctypes
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v193_extra", HERE / "bulk_aot_v193.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

BODIES = (
    bytes.fromhex("31c0c3"),
    b"\xb8" + struct.pack("<I", 0x12345678) + b"\xc3",
    bytes.fromhex("4889f8c3"),
    bytes.fromhex("89f8c3"),
    bytes.fromhex("488b4708c3"),
    bytes.fromhex("8b470cc3"),
    bytes.fromhex("48897710c3"),
    bytes.fromhex("488d4718c3"),
    bytes.fromhex("c5fa104710c3"),
    bytes.fromhex("85ff0f94c0c3"),
)

class Api(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint32), ("image_base", ctypes.c_uint64),
                ("step", ctypes.c_void_p), ("call", ctypes.c_void_p),
                ("tail", ctypes.c_void_p), ("bail", ctypes.c_void_p),
                ("trace", ctypes.c_void_p)]

class Function(ctypes.Structure):
    _fields_ = [("offset", ctypes.c_uint64), ("size", ctypes.c_uint64),
                ("hash", ctypes.c_uint64), ("fn", ctypes.c_void_p),
                ("direct", ctypes.c_void_p)]

class Vec(ctypes.Union):
    _fields_ = [("b", ctypes.c_ubyte * 32), ("f", ctypes.c_float * 8)]

class Cpu(ctypes.Structure):
    _fields_ = [("r", ctypes.c_uint64 * 16), ("rip", ctypes.c_uint64),
                ("flags", ctypes.c_uint64), ("v", Vec * 16)]

class NativeOracleTests(unittest.TestCase):
    def test_all_ten_native_functions_and_abi_negative_cases(self):
        image = b"".join(b + b"\x90" * (16 - len(b)) for b in BODIES)
        starts = list(range(0, len(image) + 1, 16))
        rows, counts = v.census(image, starts)
        self.assertEqual(tuple(r[1] for r in rows), v.KINDS)
        self.assertEqual(sum(counts.values()), 10)
        inc = HERE.parent / "recomp-v187"
        if not (inc / "recomp_abi.h").is_file():
            inc = HERE.parent / "native_recomp_bridge_v187"
        self.assertTrue((inc / "recomp_abi.h").is_file())
        with tempfile.TemporaryDirectory(prefix="v193-public-oracle-") as tmp:
            root = Path(tmp)
            out = root / "generated"
            out.mkdir()
            v.emit_private(out, image, starts, rows, 4)
            if sys.platform == "win32":
                linker_path = HERE.parent / "recomp-v188" / "win64_coff_link_v188.py"
                if not linker_path.is_file():
                    linker_path = HERE.parent / "native_coff_v188" / "win64_coff_link_v188.py"
                self.assertTrue(linker_path.is_file())
                link_spec = importlib.util.spec_from_file_location("v188_extra", linker_path)
                linker = importlib.util.module_from_spec(link_spec)
                link_spec.loader.exec_module(linker)
                dll = root / "synthetic.dll"
                linker.compile_win64(out, dll, [inc])
            else:
                clang = shutil.which("clang") or shutil.which("cc")
                self.assertIsNotNone(clang, "native C compiler required for this test")
                dll = root / "synthetic.so"
                args = [clang, "-std=c11", "-O2", "-fPIC", "-shared", "-I", str(inc)]
                args += [str(p) for p in sorted(out.glob("recomp*.c"))]
                args += ["-o", str(dll)]
                proc = subprocess.run(args, capture_output=True, timeout=90)
                self.assertEqual(proc.returncode, 0, proc.stderr[-2048:].decode(errors="replace"))
            library = ctypes.CDLL(str(dll))
            try:
                init = library.bb_recomp_init
                init.argtypes = [ctypes.POINTER(Api), ctypes.POINTER(ctypes.c_size_t)]
                init.restype = ctypes.POINTER(Function)
                api = Api()
                count = ctypes.c_size_t()
                self.assertFalse(bool(init(ctypes.byref(api), ctypes.byref(count))))
                self.assertFalse(bool(init(None, ctypes.byref(count))))
                api.version = 4
                self.assertFalse(bool(init(ctypes.byref(api), None)))
                funcs = init(ctypes.byref(api), ctypes.byref(count))
                self.assertTrue(bool(funcs))
                self.assertEqual(count.value, 10)
                self.assertEqual([funcs[i].offset for i in range(10)], [r[0] for r in rows])
                for i, (_, kind, disp) in enumerate(rows):
                    with self.subTest(kind=kind):
                        self.assertTrue(bool(funcs[i].fn))
                        self.assertTrue(bool(funcs[i].direct))
                        cpu = Cpu()
                        original_rax = 0x1122334455667788
                        original_flags = 0xfedcba9876543210
                        cpu.r[0] = original_rax
                        cpu.r[6] = 0xbeef
                        cpu.flags = original_flags
                        ctypes.memset(ctypes.addressof(cpu.v[0]), 0xa5, ctypes.sizeof(Vec))
                        buf = (ctypes.c_ubyte * 160)(*([0x3a] * 160))
                        p = ctypes.addressof(buf)
                        cpu.r[7] = p if kind in ("mem64", "mem32", "store64", "sse32") else 0x12345678
                        if kind in ("mem64", "mem32", "sse32"):
                            raw = struct.pack("<Q", 0x12345678) if kind == "mem64" else struct.pack("<I", 0x12345678)
                            ctypes.memmove(p + disp, raw, len(raw))
                        fn = ctypes.CFUNCTYPE(None, ctypes.POINTER(Cpu))(funcs[i].fn)
                        fn(ctypes.byref(cpu))
                        if kind == "zero32":
                            self.assertEqual(cpu.r[0], 0)
                            self.assertEqual(cpu.flags, (original_flags & ~v.CPU_FLAGS) | 0x44)
                        elif kind in ("imm32", "identity64", "identity32", "mem64", "mem32"):
                            self.assertEqual(cpu.r[0], 0x12345678)
                        elif kind == "store64":
                            self.assertEqual(cpu.r[0], original_rax)
                            self.assertEqual(bytes(buf[disp:disp+8]), struct.pack("<Q", 0xbeef))
                            self.assertEqual(bytes(buf[:disp]), bytes([0x3a]) * disp)
                            self.assertEqual(bytes(buf[disp+8:]), bytes([0x3a]) * (len(buf)-disp-8))
                        elif kind == "lea64":
                            self.assertEqual(cpu.r[0], 0x12345678 + disp)
                        elif kind == "sse32":
                            self.assertEqual(bytes(cpu.v[0].b[:4]), struct.pack("<I", 0x12345678))
                            self.assertEqual(bytes(cpu.v[0].b[4:]), bytes(28))
                        elif kind == "flags_eq32":
                            self.assertEqual(cpu.r[0], original_rax & ~0xff)
                            self.assertEqual(cpu.flags, (original_flags & ~v.CPU_FLAGS) | 0x4)
                            cpu.r[7] = 0
                            cpu.r[0] = original_rax
                            cpu.flags = original_flags
                            fn(ctypes.byref(cpu))
                            self.assertEqual(cpu.r[0], (original_rax & ~0xff) | 1)
                            self.assertEqual(cpu.flags, (original_flags & ~v.CPU_FLAGS) | 0x44)
                        else:
                            self.fail("Missing native oracle for grammar " + kind)
                        if kind not in ("zero32", "flags_eq32"):
                            self.assertEqual(cpu.flags, original_flags)
            finally:
                if sys.platform == "win32":
                    import _ctypes
                    _ctypes.FreeLibrary(library._handle)

if __name__ == "__main__":
    unittest.main()
