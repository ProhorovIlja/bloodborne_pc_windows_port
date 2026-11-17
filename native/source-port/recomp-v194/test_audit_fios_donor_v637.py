# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from audit_fios_donor_v637 import coverage, nid, registrations, NS


class DonorTest(unittest.TestCase):
    def setUp(self):
        self.key = ('b44anV2D7K0', (NS, 257), (NS, 1))
        self.imports = {'eboot': {self.key: [(8, 7, 0)]}}
        self.exports = {self.key: {(2, 16, 32)}}
        self.donor = registrations('REG("sceFiosFHOpenSync", hle_fios_fh_open_sync);')

    def test_exact_nid_and_overlap(self):
        self.assertEqual(nid('sceFiosFHOpenSync'), self.key[0])
        self.assertEqual(nid('sceFiosDHReadSync'), 'odjOGg8harg')
        self.imports['libc'] = self.imports['eboot'].copy()
        actual = coverage(self.imports, self.exports, self.donor)
        self.assertEqual(actual['combined'], dict(total=1, registered=['sceFiosFHOpenSync'], missing=[]))

    def test_unregistered(self):
        self.assertEqual(coverage(self.imports, self.exports, {})['combined']['missing'], [self.key[0]])

    def test_reject_wrong_reloc(self):
        self.imports['eboot'][self.key] = [(8, 6, 0)]
        with self.assertRaisesRegex(ValueError, 'import shape'):
            coverage(self.imports, self.exports, self.donor)

    def test_reject_wrong_export(self):
        self.exports[self.key] = {(1, 16, 32)}
        with self.assertRaisesRegex(ValueError, 'function export'):
            coverage(self.imports, self.exports, self.donor)

    def test_reject_duplicate_registration(self):
        line = 'REG("sceFiosFHOpenSync", hle_fios_fh_open_sync);\n'
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            registrations(line * 2)
