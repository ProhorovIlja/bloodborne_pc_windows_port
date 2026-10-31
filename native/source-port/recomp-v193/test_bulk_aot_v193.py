"""Synthetic-only tests for batch AOT. Never include any game code/assets."""
from __future__ import annotations
import ctypes
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v193',HERE/'bulk_aot_v193.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

EXAMPLES=(
    bytes.fromhex('31c0c3'),
    b'\xb8'+struct.pack('<I',0x12345678)+b'\xc3',
    bytes.fromhex('4889f8c3'),
    bytes.fromhex('89f8c3'),
    bytes.fromhex('488b4708c3'),
    bytes.fromhex('8b470cc3'),
    bytes.fromhex('48897710c3'),
    bytes.fromhex('488d4718c3'),
    bytes.fromhex('c5fa104710c3'),
    bytes.fromhex('85ff0f94c0c3'),
)

def fixture():
    image=b''.join(x+b'\x90'*(16-len(x)) for x in EXAMPLES)
    return image,list(range(0,len(image)+1,16))

class BulkSourceTests(unittest.TestCase):
    def test_real_grammar_types_from_synthetic_frames(self):
        image,starts=fixture();rows,kinds=v.census(image,starts)
        self.assertEqual(len(rows),10)
        self.assertEqual(tuple(kind for _,kind,_ in rows),v.KINDS)
        self.assertEqual(sum(kinds.values()),10)

    def test_strict_full_16_byte_and_no_hidden_code(self):
        for x in EXAMPLES:
            self.assertIsNotNone(v.classify(x+b'\x90'*(16-len(x))))
            self.assertIsNone(v.classify(x+b'\x90'*(15-len(x))+b'\xc3'))
            self.assertIsNone(v.classify(x))
        self.assertIsNone(v.classify(b'\xe8\0\0\0\0\xc3'+b'\x90'*10))

    def test_no_unsafe_memory_displacements(self):
        self.assertIsNone(v.classify(bytes.fromhex('488b47ff')+b'\xc3'+b'\x90'*11))
        self.assertIsNone(v.classify(bytes.fromhex('488b4779')+b'\xc3'+b'\x90'*11))
        self.assertIsNone(v.classify(bytes.fromhex('c5fa10477f')+b'\xc3'+b'\x90'*10))

    def test_function_bounds_and_order_are_enforced(self):
        image,starts=fixture()
        for bad in ([0,16,16],[-1,16,32],[0,1000],[],list(range(250010))):
            with self.subTest(bad=str(bad[:4])):
                with self.assertRaises(v.BulkError):v.census(image,bad)

    def test_deterministic_shards_and_full_coverage(self):
        image,starts=fixture();rows,_=v.census(image,starts)
        a=v.split_chunks(rows,3)
        self.assertEqual([len(x) for x in a],[3,3,3,1])
        self.assertEqual(sum(map(len,a)),len(rows))
        with self.assertRaises(v.BulkError):v.split_chunks(rows,0)
        with self.assertRaises(v.BulkError):v.split_chunks(rows,513)
        with self.assertRaises(v.BulkError):v.split_chunks(rows+rows,3)

    def test_private_emission_roundtrip_and_fail_closed(self):
        image,starts=fixture();rows,counts=v.census(image,starts)
        with tempfile.TemporaryDirectory(prefix='v193-synthetic-') as tmp:
            out=Path(tmp)/'out';out.mkdir()
            tampered=list(rows);tampered[4]=(tampered[4][0],'mem32',8)
            with self.assertRaises(v.BulkError):v.emit_private(out,image,starts,tampered,3)
            self.assertEqual(list(out.iterdir()),[])
            result=v.emit_private(out,image,starts,rows,3)
            self.assertEqual(result['recognized_functions'],10)
            self.assertEqual(result['source_units'],5)
            self.assertEqual(result['kinds'],10)
            manifest=json.loads((out/'PRIVATE_DO_NOT_UPLOAD_manifest.json').read_text())
            self.assertEqual(manifest['count'],10)
            self.assertEqual(len(manifest['sources_sha256']),5)
            self.assertIn('bb_recomp_init',(out/'recomp.c').read_text())
            with self.assertRaises(v.BulkError):v.emit_private(out,image,starts,rows,3)

    def test_no_private_paths_or_game_bytes_in_normal_report(self):
        for k in v.KINDS:
            self.assertNotIn('eboot',v.func_source(0,k,16).lower())
            self.assertIn('void bb_native_0',v.func_source(0,k,16))
        image,starts=fixture();rows,_=v.census(image,starts)
        with tempfile.TemporaryDirectory() as tmp:
            o=Path(tmp)/'out';o.mkdir()
            report=v.emit_private(o,image,starts,rows,3)
            for marker in ['functions','addresses','eboot','source_paths','private_manifest']:
                self.assertNotIn(marker,report)

    def test_compiled_native_module_invokes_multiple_synthetic_functions(self):
        clang=shutil.which('clang') or shutil.which('cc')
        if not clang:self.skipTest('C compiler unavailable')
        image,starts=fixture();rows,_=v.census(image,starts)
        inc=HERE.parent/'recomp-v187'
        if not (inc/'recomp_abi.h').exists():
            inc=HERE.parent/'native_recomp_bridge_v187'
        if not (inc/'recomp_abi.h').exists():self.fail('expected public V187 ABI header')
        with tempfile.TemporaryDirectory(prefix='v193-synthetic-lib-') as tmp:
            base=Path(tmp);out=base/'source';out.mkdir();v.emit_private(out,image,starts,rows,4)
            if sys.platform=='win32':
                base188=HERE.parent/'recomp-v188'/'win64_coff_link_v188.py'
                if not base188.exists():base188=HERE.parent/'native_coff_v188'/'win64_coff_link_v188.py'
                spec188=importlib.util.spec_from_file_location('link_v188',base188)
                linker=importlib.util.module_from_spec(spec188);spec188.loader.exec_module(linker)
                dll=base/'synth.dll';linker.compile_win64(out,dll,[inc]);library=ctypes.CDLL(str(dll))
            else:
                dll=base/'synth.so'
                p=subprocess.run([clang,'-fPIC','-shared','-O2','-std=c11','-I',str(inc),
                  *[str(x) for x in sorted(out.glob('recomp*.c'))],'-o',str(dll)],capture_output=True,timeout=60)
                self.assertEqual(p.returncode,0,'synthetic C compilation must succeed')
                library=ctypes.CDLL(str(dll))
            class Api(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('image_base',ctypes.c_uint64),('step',ctypes.c_void_p),('call',ctypes.c_void_p),('tail',ctypes.c_void_p),('bail',ctypes.c_void_p),('trace',ctypes.c_void_p)]
            class Function(ctypes.Structure):_fields_=[('offset',ctypes.c_uint64),('size',ctypes.c_uint64),('hash',ctypes.c_uint64),('fn',ctypes.c_void_p),('direct',ctypes.c_void_p)]
            class V(ctypes.Union):_fields_=[('b',ctypes.c_ubyte*32),('f',ctypes.c_float*8)]
            class Cpu(ctypes.Structure):_fields_=[('r',ctypes.c_uint64*16),('rip',ctypes.c_uint64),('flags',ctypes.c_uint64),('v',V*16)]
            init=library.bb_recomp_init;init.argtypes=[ctypes.POINTER(Api),ctypes.POINTER(ctypes.c_size_t)];init.restype=ctypes.POINTER(Function)
            api=Api();api.version=4;count=ctypes.c_size_t();functions=init(ctypes.byref(api),ctypes.byref(count))
            self.assertEqual(count.value,10)
            self.assertEqual([functions[i].offset for i in range(10)],[row[0] for row in rows])
            for i,(addr,kind,imm) in enumerate(rows):
                cpu=Cpu();cpu.r[0]=0x1122334455667788;cpu.r[6]=0xbeef;cpu.flags=0xfedcba9876543210
                buf=(ctypes.c_ubyte*160)(*([0x3a]*160));p=ctypes.addressof(buf)
                cpu.r[7]=p if kind in ('mem64','mem32','store64','sse32') else 0x12345678
                if kind in ('mem64','mem32','sse32'):
                    raw=struct.pack('<I',0x12345678) if kind!='mem64' else struct.pack('<Q',0x12345678)
                    ctypes.memmove(p+imm,raw,len(raw))
                fn=ctypes.CFUNCTYPE(None,ctypes.POINTER(Cpu))(functions[i].fn)
                fn(ctypes.byref(cpu))
                if kind=='imm32':self.assertEqual(cpu.r[0],0x12345678)
                if kind=='zero32':self.assertEqual(cpu.r[0],0)
                if kind=='identity64':self.assertEqual(cpu.r[0],0x12345678)
                if kind=='mem64':self.assertEqual(cpu.r[0],0x12345678)
                if kind=='store64':self.assertEqual(bytes(buf[imm:imm+8]),struct.pack('<Q',0xbeef))
                if kind=='sse32':self.assertEqual(bytes(cpu.v[0].b[:4]),struct.pack('<I',0x12345678))
            # Windows retains an open DLL lock until explicitly unloaded.
            if sys.platform=='win32':
                import _ctypes
                handle=library._handle
                del library,init,functions
                _ctypes.FreeLibrary(handle)

if __name__=='__main__':unittest.main()
