# SPDX-License-Identifier: GPL-2.0-or-later
import unittest

from cfg_v481 import walk


class TestCallFallthrough(unittest.TestCase):
    def test_selected_call_cuts_fallthrough_only(self):
        # call 10; call 11; then three returns at 10, 11 and 12.
        code = bytes.fromhex('e805000000e801000000c3c3c3')

        def decode(raw, pc):
            return (5,b'call') if raw[0] == 0xe8 else (1,b'ret')

        def run(roots, policy=None):
            seen = []
            report = walk(code,0,0,len(code),roots,set(),decode,
                          lambda pc, raw, kind, dst: seen.append((pc,dst)),
                          noreturn_call=policy)
            return report, seen

        report, seen = run({0})
        self.assertEqual((report['instructions'],seen),(4,[(0,10),(5,11)]))
        policy = lambda pc,dst: (pc,dst)==(0,10)
        report, seen = run({0},policy)
        self.assertEqual((report['instructions'],seen),(2,[(0,10)]))
        report, seen = run({0,5},policy)
        self.assertEqual((report['instructions'],seen),(4,[(0,10),(5,11)]))
