# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from module_closure_v511 import compare


def sym(typ=2, section=0, version=1):
    return dict(identity=('ABCDEFGHIJK', ('library', version), ('module', 1)),
                type=typ, section=section, binding=1)


class TestModuleClosure(unittest.TestCase):
    def test_provider_scope_and_slots(self):
        source = dict(symbols=[dict(sym(0), identity=None), sym(), sym(1), sym(version=2)],
                      relocs=[(8, 7, 1, 0), (16, 1, 1, 0), (24, 6, 2, 0), (32, 7, 3, 0)])
        provider = dict(symbols=[sym(section=1)], relocs=[])
        report = compare(dict(main=source, prx=provider))
        self.assertFalse(report['runtime_verified'])
        self.assertEqual(report['images']['main']['matches'], {
            'module:prx': dict(keys=1, slots=2, objects=0),
            'outside_supplied_modules': dict(keys=2, slots=2, objects=1),
        })
        self.assertIn('ambiguous', compare(dict(main=source, a=provider, b=provider))
                      ['images']['main']['matches'])

    def test_unsupported_and_bad_slots(self):
        source = dict(symbols=[dict(sym(0), identity=None), sym(3)], relocs=[(8, 16, 1, 0)])
        self.assertEqual(compare(dict(main=source))['images']['main'], {
            'matches': {}, 'unsupported_slots_by_reloc_and_type': {'16/3': 1},
        })
        for invalid in [(8, 16, 1, 0), (16, 7, 2, 0)]:
            with self.assertRaises(ValueError):
                compare(dict(main={**source, 'relocs': source['relocs'] + [invalid]}))
