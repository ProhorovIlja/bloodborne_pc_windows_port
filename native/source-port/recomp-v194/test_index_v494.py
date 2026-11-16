# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from io import StringIO
from index_v493 import emit_index

class Index(unittest.TestCase):
    def test_32_and_64_bit_width(self):
        for shift,bits in ((0,32),(2**32,64)):
            out=StringIO()
            self.assertEqual(emit_index([1+shift],[2+shift],{2+shift:2+shift,8+shift:2+shift},
                                        [3+shift],[4+shift],out),5)
            expected=[f'UINT{bits}_C({a+shift}),' for a in (1,2,3,4,8)]
            self.assertEqual(out.getvalue().splitlines()[1:6],expected)
            self.assertEqual(out.getvalue().splitlines()[-6:-1],
                             [f'UINT32_C({x}),' for x in (0,1,2,3,1)])

    def test_reject_invalid_routes(self):
        for params in (([1,1],[2],{2:2},[3],[4]),([1],[2],{2:3},[3],[4]),
                       ([1],[2],{5:2},[3],[4]),([1],[2],{2:2,1:2},[3],[4]),
                       ([2**64],[2],{2:2},[3],[4]),([1],[2],{2:2},[3],[3])):
            with self.assertRaises(ValueError):
                emit_index(*params,StringIO())
