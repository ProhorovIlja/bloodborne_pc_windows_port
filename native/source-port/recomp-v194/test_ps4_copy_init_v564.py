"""Synthetic regressions for offline extraction and data-only replay."""
import struct
import unittest
from ps4_pointer_triage_v562 import copy_plan, replay_copy_plan


class CopyTests(unittest.TestCase):
    def test_bounded_decode(self):
        pc, src, dst = 0x1000, 0x2000, 0x3000
        code = (b'\xc5\xf8\x28\x05'+struct.pack('<i',src-pc-8)
                +b'\xc5\xf8\x29\x05'+struct.pack('<i',dst-pc-16)+b'\xc3')
        ro = lambda a,n: (a,n)==(src,16)
        rw = lambda a,n: (a,n)==(dst,16)
        self.assertEqual(copy_plan(code,pc,ro,rw),((src,dst),))
        for i in range(len(code)):
            self.assertIsNone(copy_plan(code[:i],pc,ro,rw))
        self.assertIsNone(copy_plan(code[:9]+b'\xf9'+code[10:],pc,ro,rw))
        self.assertIsNone(copy_plan(code,pc,ro,lambda *_: False))
        self.assertIsNone(copy_plan(code,pc,lambda *_: False,rw))

    def test_replay_preflight(self):
        dst, data = 0x3000, bytearray(32)
        good = (dst,b'\xa5'*16)
        for bad in ((dst+1,b'0'*16),(dst+32,b'0'*16),
                    (dst+16,b'0'*15),(dst-16,b'0'*16)):
            with self.assertRaises(ValueError):
                replay_copy_plan(data,dst,[good,bad])
            self.assertEqual(data,bytes(32))
        replay_copy_plan(data,dst,[good])
        self.assertEqual(data,b'\xa5'*16+bytes(16))


if __name__=='__main__':
    unittest.main()
