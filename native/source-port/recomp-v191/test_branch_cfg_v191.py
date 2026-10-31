"""Synthetic-only branch/flags/CFG fixtures; no game's bytes or addresses."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import platform
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('branch_v191',HERE/'branch_cfg_v191.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def assemble(assembly, frame=32):
    """Simple *synthetic* forward-jump assembler; no game-code emitter."""
    sizes={'cmp':3,'test':2,'zero':2,'mov':5,'copy':2,'je':2,'jne':2,'jmp':2,'ret':1}
    labels={}
    offset=0
    for label,op,arg in assembly:
        if label in labels or op not in sizes:
            raise ValueError('bad fixture')
        labels[label]=offset
        offset+=sizes[op]
    if offset>frame:
        raise ValueError('fixture too big')
    out=bytearray()
    for label,op,arg in assembly:
        if op=='cmp':out+=b'\x83\xff'+struct.pack('<b',arg)
        elif op=='test':out+=b'\x85\xff'
        elif op=='zero':out+=b'\x31\xc0'
        elif op=='copy':out+=b'\x89\xf8'
        elif op=='mov':out+=b'\xb8'+struct.pack('<I',arg)
        elif op=='ret':out+=b'\xc3'
        else:
            target=labels[arg]
            delta=target-len(out)-2
            out+=bytes([{'je':0x74,'jne':0x75,'jmp':0xeb}[op]])+struct.pack('<b',delta)
    return bytes(out)+b'\x90'*(frame-len(out))


def synthetic_rows():
    first=assemble([
        ('start','cmp',7),('not7','jne','fallback'),
        ('seven','mov',0xa1b2c3d4),('toend','jmp','done'),
        ('fallback','zero',None),('check','cmp',13),('not13','jne','done'),
        ('thirteen','mov',0x12345678),('done','ret',None)])
    second=assemble([
        ('start','test',None),('zero_check','je','zero_label'),
        ('c','cmp',-3),('other','jne','high'),
        ('negative','mov',11),('jump','jmp','end'),
        ('high','mov',22),('jump2','jmp','end'),
        ('zero_label','mov',33),('end','ret',None)])
    return [dict(start=0x2000+i*64,size=len(code),code=code,ins=v.parse_cfg(code))
            for i,code in enumerate([first,second])]


class BranchAotV191Tests(unittest.TestCase):
    def test_multiple_paths_both_synthetic_forms(self):
        rows=synthetic_rows()
        self.assertEqual(len(rows),2)
        self.assertGreaterEqual(sum(sum(t in ('je','jne') for t,_,_ in row['ins'].values()) for row in rows),4)
        for row in rows:
            self.assertEqual(v.parse_cfg(row['code']),row['ins'])
            for val in (0,7,13,0xffffffff,0xfffffffd,0x100000007):
                result,flags=v.simulate(row['ins'],val)
                self.assertIsInstance(result,int)
                self.assertEqual(flags&v.DEF_FLAGS,v.simulate(row['ins'],val)[1]&v.DEF_FLAGS)

    def test_exact_expected_paths(self):
        a,b=synthetic_rows()
        self.assertEqual(v.simulate(a['ins'],7)[0],0xa1b2c3d4)
        self.assertEqual(v.simulate(a['ins'],13)[0],0x12345678)
        self.assertEqual(v.simulate(a['ins'],99)[0],0)
        self.assertEqual(v.simulate(b['ins'],0)[0],33)
        self.assertEqual(v.simulate(b['ins'],0xfffffffd)[0],11)
        self.assertEqual(v.simulate(b['ins'],1)[0],22)

    def test_reject_loop_external_branch_syscall_and_indirect_call(self):
        a=synthetic_rows()[0]['code']
        for bad in (b'\xeb\xfe'+a[2:], b'\xeb\x7f'+a[2:],
                    b'\xe8\0\0\0\0'+a[5:],
                    b'\x0f\x05'+a[2:], b'\xff\xd0'+a[2:]):
            with self.assertRaises(v.CFGError):
                v.parse_cfg(bad)

    def test_reject_middle_of_instruction_and_non_nop_tail(self):
        a=bytearray(synthetic_rows()[0]['code'])
        # JE immediate landing inside the MOV imm32 rather than an opcode.
        a[4]=2
        with self.assertRaises(v.CFGError):v.parse_cfg(bytes(a))
        a=bytearray(synthetic_rows()[0]['code']);a[-1]=0xff
        with self.assertRaises(v.CFGError):v.parse_cfg(bytes(a))
        a=bytearray(synthetic_rows()[0]['code']);a[-1]=0xc3
        with self.assertRaises(v.CFGError):v.parse_cfg(bytes(a))

    def test_reject_undefined_return_register_even_if_branch_is_well_formed(self):
        body=assemble([('test','test',None),('j0','je','bare'),
                       ('v','mov',99),('cmp','cmp',17),('j1','jne','bare'),
                       ('bare','ret',None)])
        with self.assertRaisesRegex(v.CFGError,'unknown incoming'):
            v.parse_cfg(body)

    def test_reject_drift_and_private_dir_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'keep.txt').write_text('do not overwrite')
            with self.assertRaisesRegex(v.CFGError,'empty'):
                v.emit_private(p,synthetic_rows())
            self.assertEqual((p/'keep.txt').read_text(),'do not overwrite')
        with self.assertRaisesRegex(v.CFGError,'sample'):
            v.select(b'\0'*256,list(range(0,128,16)))

    def test_original_cpu_differential_synthetic_only(self):
        if platform.system()!='Linux' or platform.machine()!='x86_64':
            self.skipTest('Linux x86-64 W^X original byte oracle only')
        self.assertEqual(v.original_cpu_oracle(synthetic_rows()),2*len(v.test_values()))

    def test_native_compiled_paths_and_flags_linux_and_win64(self):
        if platform.system() not in ('Linux','Windows'):
            self.skipTest('unsupported CPU/OS')
        rows=synthetic_rows()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'private_synthetic_source';source.mkdir()
            v.emit_private(source,rows)
            self.assertEqual(sorted(p.name for p in source.iterdir()),['recomp.c','recomp_1.c'])
            if platform.system()=='Linux':
                count=v.compile_linux(source,rows)
            else:
                bpath=HERE.parent/'recomp-v188'/'win64_coff_link_v188.py'
                spec=importlib.util.spec_from_file_location('coff_v188',bpath)
                tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
                dst=root/'synthetic_branch.dll'
                outcome=tool.compile_win64(source,dst,[v.v189.abi_dir()])
                self.assertTrue(outcome['bb_recomp_init_export_present'])
                count=v.probe_compiled(dst,rows)
            self.assertEqual(count,2*len(v.test_values()))

if __name__=='__main__':unittest.main()
