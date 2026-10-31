"""Synthetic only fixtures; never contains any original Bloodborne code or offsets."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import platform
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v192_synthetic',HERE/'call_graph_v192.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def fixtures():
    # These invented addresses/imm constants intentionally differ from private game.
    mapping={
        0x200:('call-mask32',0x900,0),
        0x300:('call-mask32',0x900,0),
        0x400:('call-add64',0xa00,0x13579bdf),
    }
    image=bytearray(4096)
    starts=[0x200,0x220,0x300,0x320,0x400,0x420,0x900,0x910,0xa00,0xa10]
    for addr,(kind,target,extra) in mapping.items():
        caller=b'\x55\x48\x89\xe5\xe8'+struct.pack('<i',target-addr-9)
        if kind=='call-mask32':caller+=b'\x89\xc1\xc1\xf9\x1f\x21\xc1\x89\xc8\x5d\xc3'
        else:caller+=b'\x48\x05'+struct.pack('<I',extra)+b'\x5d\xc3'
        image[addr:addr+32]=caller+b'\x90'*(32-len(caller))
    image[0x900:0x910]=b'\x31\xc0\xc3'+b'\x90'*13
    image[0xa00:0xa10]=b'\xb8'+struct.pack('<I',0x2468ace0)+b'\xc3'+b'\x90'*10
    return bytes(image),starts

class RealPairGenericV192(unittest.TestCase):
    def setUp(self):
        self.image,self.starts=fixtures()
        self.rows=v.select(self.image,self.starts)

    def test_strict_three_actual_call_templates(self):
        self.assertEqual(len(self.rows),3)
        self.assertEqual([r['kind'] for r in self.rows],['call-mask32','call-mask32','call-add64'])
        self.assertEqual(len({r['target'] for r in self.rows}),2)
        for r in self.rows:
            self.assertEqual(len(r['caller']),32)
            self.assertEqual(len(r['callee']),16)
            self.assertEqual(v.parse_caller(r['caller'])[0],r['kind'])
            self.assertIn(v.parse_target(r['callee'])[0],('zero32','imm32'))
            self.assertEqual(r['start']+9+struct.unpack_from('<i',r['caller'],5)[0],r['target'])

    def test_machine_flags_and_expected_call_effect(self):
        for r in self.rows:
            result,flags=v.expected(r)
            self.assertIsInstance(result,int)
            self.assertIn(flags&v.DEF_FLAGS,(0x44, v.expected(r)[1]&v.DEF_FLAGS))
        self.assertEqual(v.expected(self.rows[-1])[0],(0x2468ace0+0x13579bdf)&0xffffffffffffffff)

    def test_invalid_call_target_exact_fde_required(self):
        image=bytearray(self.image)
        image[0x200+5:0x200+9]=struct.pack('<i',0x901-(0x200+9))
        with self.assertRaisesRegex(v.PairError,'exact original FDE'):
            v.bind_pair(bytes(image),self.starts,0x200,0x901)
        with self.assertRaisesRegex(v.PairError,'resolves elsewhere'):
            v.bind_pair(bytes(image),self.starts,0x200,0x900)

    def test_unknown_callee_callsite_and_hidden_instructions_refused(self):
        for addr in (0x200,0x400):
            image=bytearray(self.image)
            image[addr+9]=0xff
            with self.assertRaises(v.PairError):
                v.parse_caller(bytes(image[addr:addr+32]))
            image=bytearray(self.image)
            image[addr+31]=0xcc
            with self.assertRaises(v.PairError):
                v.parse_caller(bytes(image[addr:addr+32]))
        image=bytearray(self.image)
        image[0xa00]=0xe8  # callee now calls another function, unsafe
        with self.assertRaises(v.PairError):
            v.bind_pair(bytes(image),self.starts,0x400,0xa00)

    def test_no_overwrite_and_no_nonempty_private_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'important.txt').write_text('do not touch')
            with self.assertRaisesRegex(v.PairError,'new empty'):
                v.emit_private(root,self.rows)
            self.assertEqual((root/'important.txt').read_text(),'do not touch')

    def test_reject_unexpected_source_sample(self):
        with self.assertRaises(v.PairError):v.select(b'\0'*1024,list(range(0,1024,16)))
        with self.assertRaises(v.PairError):v.select(self.image,self.starts,limit=20)
        with self.assertRaises(v.PairError):v.parse_caller(b'\x90'*32)
        with self.assertRaises(v.PairError):v.parse_target(b'\x90'*16)

    def test_actual_x86_cpu_synthetic_call_stack_differential(self):
        if platform.system()!='Linux' or platform.machine()!='x86_64':
            self.skipTest('Linux x86_64 only W^X actual CPU oracle')
        self.assertEqual(v.cpu_oracle(self.rows),3*len(v.VALUES))

    def test_native_compiled_interprocedural_calls_and_flags(self):
        if platform.system() not in ('Linux','Windows'):
            self.skipTest('Windows/Linux only')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'private_synthetic_test';source.mkdir()
            v.emit_private(source,self.rows)
            self.assertEqual({p.name for p in source.iterdir()},{'recomp.c','recomp_1.c'})
            if platform.system()=='Linux':
                count=v.compile_linux(source,self.rows)
            else:
                spec=importlib.util.spec_from_file_location('win64_v188',HERE.parent/'recomp-v188'/'win64_coff_link_v188.py')
                tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
                dll=root/'synthetic_call_v192.dll'
                status=tool.compile_win64(source,dll,[v.v189.abi_dir()])
                self.assertTrue(status['bb_recomp_init_export_present'])
                count=v.probe_compiled(dll,self.rows)
            self.assertEqual(count,3*len(v.VALUES))

    def test_canonical_long_nop_accepted_but_random_tail_refused(self):
        self.assertTrue(v.valid_alignment_nop(b'\x66'*6+b'\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00'))
        self.assertFalse(v.valid_alignment_nop(b'\x66'*7+b'\x2e\x0f\x1f\x84\x00\x00\x00\x00\x00'))
        self.assertFalse(v.valid_alignment_nop(b'\x66'*6+b'\x2e\x0f\x1f\x84\x00\x00\x00\x00\x01'))

if __name__=='__main__':unittest.main()
