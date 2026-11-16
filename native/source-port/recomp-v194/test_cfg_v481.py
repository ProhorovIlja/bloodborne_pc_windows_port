# SPDX-License-Identifier: GPL-2.0-or-later
import os
import unittest
from cfg_v481 import edge, llvm, walk


class Flow(unittest.TestCase):
    def test_encoding(self):
        for raw,m,expected in (
            ('e8fcffffff',b'callq',('call',-4)),
            ('e9faffffff',b'jmp',('jump',-6)),
            ('ebfe',b'jmp',('jump',-2)),
            ('7503',b'jne',('conditional',3)),
            ('0f8402000000',b'je',('conditional',2)),
            ('67e3fc',b'jecxz',('conditional',-4)),
            ('c7f800000000',b'xbegin',('conditional',0)),
            ('41ffd0',b'callq',('indirect_call',None)),
            ('3effe0',b'jmpq',('indirect_jump',None)),
            ('ff28',b'ljmp',('unknown',None)),
        ):
            self.assertEqual(edge(bytes.fromhex(raw),m),expected)

    def test_walk(self):
        # 0 call 12; 5 jnz 10; 7 indirect call; 9 ret; 10 indirect jump;
        # 12 ret; 13 unknown; 14 syscall; 16 jump out; 18 decode failure.
        image=bytes.fromhex('e8070000007503ffd0c3ffe0c3900f05eb7f0f')
        ins={0:(5,b'callq'),5:(2,b'jne'),7:(2,b'callq'),9:(1,b'retq'),
             10:(2,b'jmpq'),12:(1,b'retq'),13:(1,b'jnew'),14:(2,b'syscall'),16:(2,b'jmp')}
        report=walk(image,0,100,len(image),{100,101,113,114,116,118},{101,112,118},
                    lambda raw,a:ins.get(a-100,(0,b'')))
        for k,v in dict(instructions=9,call=1,conditional=1,indirect_call=1,indirect_jump=1,
                        failed=1,out_of_rx=1,unknown=1,system=1,overlap=1,
                        decoded_new_call_targets=1,relocation_targets_at_decoded_starts=1).items():
            self.assertEqual(report[k],v,k)

    @unittest.skipUnless(os.environ.get('BB_V481_LLVM'),'LLVM fixture opt-in')
    def test_llvm(self):
        image=bytes.fromhex('e8070000007503ffd0c3ffe0c3')
        decode,close=llvm(os.environ['BB_V481_LLVM'])
        try:
            r=walk(image,0,0,len(image),{0},{12},decode)
        finally:
            close()
        for k in ('call','conditional','indirect_call','indirect_jump','decoded_new_call_targets'):
            self.assertEqual(r[k],1,k)
        self.assertEqual(r['instructions'],6)
