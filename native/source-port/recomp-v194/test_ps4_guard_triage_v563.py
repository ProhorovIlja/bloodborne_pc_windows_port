"""Exercise guard analysis without a retail image."""
import unittest
from ps4_pointer_triage_v562 import guard_prefix, guarded_counts


class GuardTests(unittest.TestCase):
    short = bytes.fromhex('488d05f90000008038007504')
    near = bytes.fromhex('488d05f90000008038000f8504000000')

    def test_decode(self):
        self.assertEqual(guard_prefix(self.short,0x1000),(0x1100,0x1010,12))
        self.assertEqual(guard_prefix(self.near,0x1000),(0x1100,0x1014,16))
        for bad in (self.short[:11], self.short[:10]+b'\x74'+self.short[11:],
                    self.short[:9]+b'\x01'+self.short[10:], self.near[:15]):
            self.assertIsNone(guard_prefix(bad,0x1000))

    def test_zero_fill_guard(self):
        b = self.short+b'\x90\xc6\x00\x01\xc3'
        def offset(a,n,flags):
            return a-0x1000 if flags==1 and 0x1000<=a<=0x1000+len(b)-n else None
        def writable(a):
            return a==0x1100
        r = guarded_counts(b,{0x1000:3},0x1200,offset,writable)
        self.assertEqual(r,dict(guard_prefix_targets=1,guard_prefix_slots=3,
            guard_branch_ret_targets=1,guard_set_then_ret_targets=1,
            distinct_guard_bytes=1,shared_guard_bytes=0))
        self.assertEqual(guarded_counts(b,{0x1000:3},0x1200,offset,lambda _:False)['guard_prefix_targets'],0)
        self.assertEqual(guarded_counts(b,{0x1000:3},0x1010,offset,writable)['guard_prefix_targets'],0)


if __name__=='__main__':
    unittest.main()
