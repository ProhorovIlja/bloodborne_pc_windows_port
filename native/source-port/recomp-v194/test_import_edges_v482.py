# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest
from import_edges_v482 import Edges,rip_slot

class ImportEdges(unittest.TestCase):
    def test_slot(self):
        self.assertEqual(rip_slot(100,bytes.fromhex('ff15faffffff'),'indirect_call'),100)
        self.assertEqual(rip_slot(100,bytes.fromhex('3eff2501000000'),'indirect_jump'),108)
        for raw in ('67ff2501000000','64ff2501000000','ffd0','ff1500000000'):
            self.assertIsNone(rip_slot(100,bytes.fromhex(raw),'indirect_jump'))

    def test_provenance(self):
        image=bytearray(64)
        image[:16]=struct.pack('<2siBiBi',b'\xff\x25',200-106,0x68,3,0xe9,132-116)
        image[32:48]=bytes.fromhex('ff3500000000ff250000000090909090')
        key=(b'ABCDEFGHIJK',b'L',b'M',2)
        evidence=dict(rx=(1,5,0,100,0,64,64,1),relocs={200:(7,0),208:(8,120)},plt_order={200:3})
        e=Edges(image,evidence,{200:(7,0,key)})
        e.observe(50,b'', 'call',100)
        e.observe(100,image[:6],'indirect_jump',None)
        e.observe(100,b'\xff\x15'+struct.pack('<i',102),'indirect_call',None)
        e.observe(100,b'\xff\xd0','indirect_call',None)
        self.assertEqual(e.summary()['sites'],{'plt_call':1,'indirect_jump_function_import':1,
            'indirect_call_relative_rx_candidate':1,'indirect_call_other_operand':1})
        self.assertEqual(e.summary()['distinct_import_keys'],1)
        for i in (6,7,11,12,32,44):
            bad=image[:]
            bad[i]^=255
            self.assertIsNone(Edges(bad,evidence,{200:(7,0,key)}).thunk(100))
