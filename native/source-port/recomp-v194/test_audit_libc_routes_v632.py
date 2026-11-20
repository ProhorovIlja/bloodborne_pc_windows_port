# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from audit_libc_routes_v632 import coverage, read_routes


class CoverageTest(unittest.TestCase):
    key = ('nid', ('libc', 257), ('libc', 1))

    def test_routes_are_full_identities(self):
        row = 'nid\tlibc\t257\tlibc\t1\n'
        self.assertEqual(read_routes(row), {self.key})
        for bad in ('', row + row, row.replace('257', 'invalid')):
            with self.assertRaises(ValueError):
                read_routes(bad)

    def test_counts_slots_without_confusing_them_with_identities(self):
        obj = ('obj', *self.key[1:])
        other = ('nid', ('libc', 258), self.key[2])
        game = {'imports': {self.key: [(1, 7, 0), (2, 1, 8)], obj: [(3, 1, 16)], other: [(4, 7, 0)]}}
        libc = {'exports': {self.key: {(2, 10, 2)}, obj: {(1, 12, 24)}, other: {(2, 11, 1)}}}
        fios = {'imports': {self.key: [(5, 7, 0)]}}
        got = coverage([game, libc, fios], {self.key})
        self.assertEqual(got['eboot']['identities'],
                         {'route_candidate': 1, 'uncovered_object': 1, 'uncovered_function': 1})
        self.assertEqual(got['eboot']['sites'], {'route_candidate:7': 1, 'route_candidate:1': 1,
                                                'route_candidate:nonzero_addend': 1,
                                                'uncovered_object:1': 1, 'uncovered_function:7': 1})
        self.assertEqual(got['fios2']['identities'], {'route_candidate': 1})

    def test_rejects_invalid_provider_claims(self):
        game = {'imports': {self.key: [(1, 7, 0)]}}
        good = {'exports': {self.key: {(2, 10, 2)}}}
        bad_type = {'exports': {self.key: {(1, 10, 2)}}}
        ambiguous = {'exports': {self.key: {(2, 10, 2), (2, 30, 2)}}}
        for images in ([{}, good, {}], [game, {}, {}], [game, bad_type, {}],
                       [game, ambiguous, {}], [game, good, good]):
            with self.assertRaises(ValueError):
                coverage(images, {self.key})


if __name__ == '__main__':
    unittest.main()
