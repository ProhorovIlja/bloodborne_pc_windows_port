# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest

from audit_switch_v507 import compare


class TestSwitchAudit(unittest.TestCase):
    def test_same_targets_wrong_order_and_unproven_target(self):
        image = bytearray(96)
        image[8:30] = bytes.fromhex('4883f8027716488d152b00000048630c824801d1ffe1')
        struct.pack_into('<iii', image, 64, -32, -16, -32)
        rx = (1, 5, 16, 256, 0, 96, 96, 1)
        row = dict(entry=264, table=320, default=292, targets=[288, 304, 288])
        evidence = dict(image_sha256='fixture', switches=[row])
        def run():
            return compare(bytes(16)+image, 'fixture', rx, evidence)
        self.assertEqual(run(), dict(checked=1, matched=1, rejected=0, mismatched=0,
                                     runtime_verified=False))
        row['targets'] = [304, 288, 288]
        self.assertEqual(run()['mismatched'], 1)
        row['targets'] = [304, 308, 304]
        self.assertEqual(run()['rejected'], 1)
        evidence['switches'] = [row, row]
        with self.assertRaises(ValueError):
            run()
        evidence['switches'] = [row]
        evidence['image_sha256'] = 'wrong'
        with self.assertRaises(ValueError):
            run()
