"""Synthetic-only regression suite for the private Bloodborne ELF leaf translator.
CI never needs actual retail Bloodborne bits or hashes from private artifacts.
"""
import importlib.util
import hashlib
import os
from pathlib import Path
import platform
import struct
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('source_v189',HERE/'real_leaf_recomp_v189.py')
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

TAIL=b'\x90'*16
OPCODES=[b'\x31\xc0\xc3',b'\xb8\x34\x12\x00\x00\xc3',b'\x48\x89\xf8\xc3',b'\x89\xf8\xc3']

def mkfixture(path: Path):
    """Build an original-SCE-layout TEST binary, with SYNTHETIC instruction fragments."""
    memsize=0x20000
    image=bytearray(memsize)
    first_len=0x18000
    count=1002
    eh=0x10000
    for i in range(count):
        addr=0xa0+16*i
        body=OPCODES[i] if i<len(OPCODES) else b'\x31\xc0\xc3'
        image[addr:addr+16]=body+b'\x90'*(16-len(body))
    image[eh:eh+4]=b'\x01\x1b\x03\x3b'
    struct.pack_into('<iI',image,eh+4,-12,count)
    for i in range(count):
        addr=0xa0+16*i
        struct.pack_into('<ii',image,eh+12+i*8,addr-eh,0)
    # Header is in file before first PT_LOAD, as in genuine PS4 ELF.
    foff=0x400
    data=bytearray(foff+first_len)
    data[:7]=b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HH',data,16,0xfe10,62)
    struct.pack_into('<Q',data,32,64)
    struct.pack_into('<HH',data,54,56,3)
    ph=[(1,5,foff,0,0,first_len,first_len,0x4000),
        (1,6,foff+first_len,first_len,0,0,memsize-first_len,0x4000),
        (0x6474e550,4,foff+eh,eh,0,12+count*8,12+count*8,4)]
    for i,p in enumerate(ph):struct.pack_into('<IIQQQQQQ',data,64+i*56,*p)
    data[foff:foff+first_len]=image[:first_len]
    path.write_bytes(data)
    return bytes(image)

class PrivateLeafV189Tests(unittest.TestCase):
    def test_restricted_decoder_has_no_branches_or_memory(self):
        for op,kind in zip(OPCODES,v.PATTERNS):
            self.assertEqual(v.identify(op)[0],kind)
            self.assertIsNone(v.identify(b'\xe8'+op)) # call
            self.assertIsNone(v.identify(b'\x48\x8b\x07\xc3')) # load
            self.assertIsNone(v.identify(b'\x75\x02'+op)) # branch
        self.assertIsNone(v.identify(b'\xc3'))

    def test_synthetic_elf_fde_sha_and_cpu_oracle(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'synthetic.elf'
            image=mkfixture(p)
            with patch.object(v,'IMAGE_SHA',hashlib.sha256(image).hexdigest()),patch.object(v,'EXPECTED_SIZE',len(image)):
                read,starts=v.load_original(p)
                fs=v.select(read,starts)
                self.assertEqual([v.identify(x[3])[0] for x in fs],list(v.PATTERNS))
                self.assertEqual(len(starts),1002)
                if platform.system()=='Linux' and platform.machine()=='x86_64':
                    self.assertEqual(v.cpu_oracle(fs,iterations=4),48)
                dest=Path(td)/'generated'
                dest.mkdir()
                v.emit_private_c(dest,fs)
                self.assertEqual(sorted(x.name for x in dest.iterdir()),['recomp.c','recomp_1.c'])
                self.assertEqual((dest/'recomp.c').read_text().count('game_leaf_'),12)
            with patch.object(v,'EXPECTED_SIZE',len(image)):
                with self.assertRaisesRegex(v.ProofError,'SHA'):
                    v.load_original(p)

    def test_fde_rejects_nonpadding_executable_tail(self):
        image=bytearray(512)
        start=160
        image[start:start+16]=b'\x31\xc0\xc3'+b'\x90'*12+b'\x75'
        for n in range(4):
            image[start+16+n*16:start+16+(n+1)*16]=OPCODES[n]+b'\x90'*(16-len(OPCODES[n]))
        fs=v.select(bytes(image),[start+16*i for i in range(6)])
        self.assertEqual(len(fs),4)
        self.assertNotEqual(fs[0][0],start)

    def test_private_output_is_guarded(self):
        data=[(32,3,0,OPCODES[0])]*4
        with tempfile.TemporaryDirectory() as t:
            d=Path(t)
            (d/'unrelated.txt').write_text('do not overwrite')
            with self.assertRaisesRegex(v.ProofError,'empty'):
                v.emit_private_c(d,data)

    def test_wrong_game_or_corrupt_phdr_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'synthetic.elf'
            mkfixture(p)
            c=bytearray(p.read_bytes())
            c[18]=0
            p.write_bytes(c)
            with self.assertRaisesRegex(v.ProofError,'x86-64'):
                v.load_original(p)
            c[18]=62
            # Bad ELF program header directory offset.
            struct.pack_into('<Q',c,32,len(c)+1000)
            p.write_bytes(c)
            with self.assertRaisesRegex(v.ProofError,'program header'):
                v.load_original(p)

    def test_unsupported_original_cpu_oracle_platform(self):
        with patch.object(v.platform,'system',return_value='Windows'):
            with self.assertRaisesRegex(v.ProofError,'Linux'):
                v.cpu_oracle([])

if __name__ == '__main__': unittest.main()
