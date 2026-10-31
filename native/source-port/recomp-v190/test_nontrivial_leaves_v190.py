"""V190 PUBLIC synthetic fixtures only. Never use a retail game in GitHub CI."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import platform
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('nontrivial_v190',HERE/'nontrivial_leaves_v190.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# All six are hand-written synthetic machine-code fixture instructions.
FIXTURE=(
    ('mem64',bytes.fromhex('488b4710c3'),16),
    ('mem32',bytes.fromhex('8b4708c3'),8),
    ('store64',bytes.fromhex('48897730c3'),48),
    ('lea64',bytes.fromhex('488d4710c3'),16),
    ('sse32',bytes.fromhex('c5fa10471cc3'),28),
    ('flags_eq32',bytes.fromhex('85ff0f94c0c3'),0),
)


def synthetic_rows():
    return [dict(kind=k,start=0x1000+16*i,size=len(op),offset=off,code=op)
            for i,(k,op,off) in enumerate(FIXTURE)]


class NontrivialPrivateAotV190Tests(unittest.TestCase):
    def test_all_six_synthetic_instr_grammars(self):
        self.assertEqual(len(v.KINDS),6)
        for kind,op,off in FIXTURE:
            with self.subTest(kind=kind):
                self.assertEqual(v.decode(op),(kind,len(op),off))
                self.assertEqual(v.decode(op+b'\x90'*(16-len(op))),
                                 (kind,len(op),off))

    def test_safe_x86_nop_grammar_and_negative_drift(self):
        self.assertTrue(v.valid_nops(bytes.fromhex('66662e0f1f840000000000')))
        self.assertFalse(v.valid_nops(bytes.fromhex('90e801000000')))
        self.assertFalse(v.valid_nops(bytes.fromhex('90c3')))
        self.assertFalse(v.valid_nops(bytes.fromhex('662e0f1f840000000001')))
        self.assertFalse(v.valid_nops(bytes.fromhex('6666666666666666')))
        for kind,op,off in FIXTURE:
            with self.subTest(kind=kind):
                self.assertIsNone(v.decode(op[:-1]+b'\x90'))
                self.assertIsNone(v.decode(op+b'\xe8'))
        self.assertIsNone(v.decode(bytes.fromhex('488b47ffc3')))  # negative disp
        self.assertIsNone(v.decode(bytes.fromhex('488b4779c3')))  # OOB mem
        self.assertIsNone(v.decode(bytes.fromhex('488b4700ffe0')))  # jmp reg
        self.assertIsNone(v.decode(bytes.fromhex('648b4708c3')))  # TLS

    def test_original_fde_scanner_uses_exact_16_and_every_kind(self):
        image=bytearray(8192)
        starts=[]
        for i,(_,op,_) in enumerate(FIXTURE):
            addr=0x1000+16*i
            image[addr:addr+16]=op+b'\x90'*(16-len(op))
            starts.append(addr)
        starts.append(0x1000+16*len(FIXTURE))
        rows=v.select(bytes(image),starts)
        self.assertEqual([r['kind'] for r in rows],list(v.KINDS))
        with self.assertRaisesRegex(v.GateError,'unavailable'):
            v.select(bytes(image),starts[:-1])
        image[0x1000+len(FIXTURE[0][1])]=0xE8
        with self.assertRaisesRegex(v.GateError,'unavailable'):
            v.select(bytes(image),starts)

    def test_synthetic_original_cpu_on_linux(self):
        if platform.system()!='Linux' or platform.machine()!='x86_64':
            self.skipTest('actual machine-code fixture CPU oracle runs only on Linux x64')
        self.assertEqual(v.cpu_oracle(synthetic_rows(),iterations=2),72)

    def test_private_output_refuses_existing_data(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'existing.txt').write_text('not owned by this test')
            with self.assertRaisesRegex(v.GateError,'empty'):
                v.emit(p,synthetic_rows())
            self.assertEqual((p/'existing.txt').read_text(),'not owned by this test')
        with self.assertRaisesRegex(v.GateError,'incomplete'):
            with tempfile.TemporaryDirectory() as d:v.emit(Path(d),synthetic_rows()[:2])

    def test_real_native_platform_compiles_and_checks_synthetic_all_six(self):
        if platform.system() not in ('Windows','Linux'):
            self.skipTest('native Windows/Linux only')
        rows=synthetic_rows()
        with tempfile.TemporaryDirectory() as d:
            private=Path(d)/'synthetic_generated';private.mkdir()
            v.emit(private,rows)
            self.assertEqual({p.name for p in private.iterdir()},{'recomp.c','recomp_1.c'})
            if platform.system()=='Linux':
                self.assertEqual(v.compile_probe(private,rows),444)
            else:
                branch=v.HERE if hasattr(v,'HERE') else HERE
                bridge=HERE.parent/'recomp-v188'/'win64_coff_link_v188.py'
                bs=importlib.util.spec_from_file_location('win64_v188',bridge)
                b=importlib.util.module_from_spec(bs);bs.loader.exec_module(b)
                dll=Path(d)/'nontrivial_test.dll'
                report=b.compile_win64(private,dll,[v.v189.abi_dir()])
                self.assertEqual(report['source_units_compiled'],2)
                self.assertTrue(report['bb_recomp_init_export_present'])
                self.assertEqual(v.probe_compiled_library(dll,rows),444)

if __name__=='__main__':unittest.main()
