# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from random import Random
import tempfile
import unittest

from guest_payload_v517 import EH, PH, anchors, contains


class TestGuestPayload(unittest.TestCase):
    def test_raw_wrapped_and_unrelated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, candidate = root/'source', root/'candidate'
            data = Random(517).randbytes(16384)
            header = EH.pack(b'\x7fELF\x02\x01\x01',0xfe10,62,1,0,64,0,0,64,56,1,0,0,0)
            src.write_bytes(header+PH.pack(1,5,120,0,0,len(data),len(data),1)+data)
            sig = anchors(src)
            self.assertEqual(len(sig),3)
            for payload, expected in ((data,True),(b'host prefix'+data+b'footer',True),
                                      (data[:4096],False),(bytes(len(data)),False),(b'',False)):
                candidate.write_bytes(payload)
                with candidate.open('rb') as f:
                    self.assertEqual(contains(f,sig),expected)
            src.write_bytes(header)
            with self.assertRaises(ValueError):
                anchors(src)
