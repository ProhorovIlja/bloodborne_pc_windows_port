# SPDX-License-Identifier: GPL-2.0-or-later
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from census_v480 import EH, PH, LIMIT, census, compare_v204, summarize


def fixture():
    im=bytearray(1400)
    EH.pack_into(im,0,b'\x7fELF\x02\x01\x01'+bytes(9),0xfe10,62,1,0x1000,64,0,0,64,56,5,0,0,0)
    parts=[(1,5,384,0x1000,0,512,512,1),(1,6,896,0x2000,0,64,128,1),
           (0x6474e550,4,640,0x1100,0,20,20,1),(2,4,960,0,0,64,64,1),
           (0x61000000,4,1024,0,0,72,72,1)]
    for i,row in enumerate(parts):
        PH.pack_into(im,64+56*i,*row)
    im[394:397]=b'\x48\x8d\x1d'
    struct.pack_into('<i',im,397,0x2018-0x1011)
    im[468:471]=b'\x48\x8b\x03'
    struct.pack_into('<4siIii',im,640,b'\x01\x1b\x03\x3b',0x1080-0x1104,1,0,0x10a0-0x1100)
    struct.pack_into('<IIi',im,544,12,0x24,0x1100-0x10a8)
    struct.pack_into('<Q',im,896,LIMIT-1)
    struct.pack_into('<8Q',im,960,12,0x1000,0x6100002f,0,0x61000031,72,0,0)
    struct.pack_into('<QQqQQqQQq',im,1024,0x2018,8,0x1100,0x2008,8,0x1010,0x2028,8,0x1110)
    return im


class TestCensus(unittest.TestCase):
    def test_projection(self):
        groups,n=census(fixture(),0x2018)
        self.assertEqual(n,2)
        report=summarize(groups,n,{0x1010,0x1100,0x1190},{0x1100})
        self.assertEqual(report['metadata_candidate_ids'],4)
        self.assertEqual(report['scanner_comparison']['scanner_only'],1)
        self.assertEqual(report['emitted_comparison']['scan_not_emitted'],2)
        self.assertEqual(report['emitted_comparison']['missing_by_group']['constructors'],1)
        self.assertFalse(report['full_native_coverage_attested'])
        with self.assertRaises(ValueError):
            summarize(groups,n,{0x1010},{0x1100})

    def test_corruption(self):
        with self.assertRaises(ValueError):
            census(fixture(),0x2020)
        for pos in (896, 394, 640, 552, 1032):
            im=fixture()
            im[pos]^=255
            with self.assertRaises(ValueError, msg=str(pos)):
                census(im,0x2018)

        im=fixture()
        struct.pack_into('<Q',im,1072,0x2018)
        with self.assertRaises(ValueError):
            census(im,0x2018)

    def test_v204_attested_inputs(self):
        image=fixture()
        index=b'address\tsize\tinstructions\tundecodable\n0x1010\t3\t1\t0\n0x1100\t3\t1\t0\n'
        generated=b'static const RcFunction table[] = {\n{0x1100, 3, 0x9ull, f_1100, &d_1100},\n};\n'
        sha=lambda b:hashlib.sha256(b).hexdigest()
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            (root/'scan').mkdir()
            (root/'generated').mkdir()
            scan=root/'scan/functions.tsv'
            table=root/'generated/recomp.c'
            scan.write_bytes(index)
            table.write_bytes(generated)
            meta=dict(format='SHYT_PRIVATE_FULL_IMAGE_V204', upstream='8f31ec7c41f252730c6325d52647046baef7549f',
                original_size_bytes=len(image), input_sha256=sha(image), scanner_index_sha256=sha(index),
                c_hashes={'recomp.c':sha(generated)}, functions_scanned=2, aot_functions_registered=1,
                functions_not_in_aot_table=1, complete_scanner_to_aot_registration=False)
            (root/'full-original-preparation.json').write_text(json.dumps(meta),encoding='utf-8')
            self.assertEqual(compare_v204(image,root),({0x1010,0x1100},{0x1100}))
            for file, data in ((scan,index),(table,generated)):
                file.write_bytes(data+b' ')
                with self.assertRaises(ValueError):
                    compare_v204(image,root)
                file.write_bytes(data)
            image[-1]^=1
            with self.assertRaises(ValueError):
                compare_v204(image,root)
