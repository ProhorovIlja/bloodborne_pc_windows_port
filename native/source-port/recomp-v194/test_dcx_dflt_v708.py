# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise DCX framing, using independent Go zlib streams as input."""
from pathlib import Path
from random import Random
import struct
import subprocess
from tempfile import TemporaryDirectory
import unittest

from dcx_dflt_v708 import HEADER, VARIANTS, unpack

GO = '''package main
import("compress/zlib";"io";"os")
func main() {
    w := zlib.NewWriter(os.Stdout)
    if _, err := io.Copy(w, os.Stdin); err != nil { panic(err) }
    if err := w.Close(); err != nil { panic(err) }
}
'''


def container(payload, size, variant):
    version, kind, level, flags = variant
    return HEADER.pack(b'DCX\0',version,24,36,kind,kind+8,b'DCS\0',size,len(payload),
                       b'DCP\0',b'DFLT',32,level<<24,0,flags<<24,0,0x10100,b'DCA\0',8)+payload


class DcxTests(unittest.TestCase):
    def test_go_streams_and_bad_framing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'main.go'
            source.write_text(GO)
            subprocess.run(['go','build','-o',root/'enc',source],check=True)
            rng = Random(708)
            good = bad = 0
            for i in range(128):
                raw = (b'', b'BND4'+b'a'*65536, rng.randbytes(i*61), b'TPF\0'*i)[i%4]
                stream = subprocess.check_output([root/'enc'],input=raw,timeout=5)
                for variant in sorted(VARIANTS):
                    dcx = container(stream,len(raw),variant)
                    self.assertEqual(unpack(dcx,max_output=len(raw)),raw)
                    good += 1
                    corrupt = stream[:-1]+bytes([stream[-1]^1])
                    size = len(raw)
                    for data, limit in (
                        (dcx[:-1],size), (dcx+b'\0',size), (dcx[:75],size),
                        (container(corrupt,size,variant),size),
                        (container(stream[:-1],size,variant),size),
                        (container(stream+stream,size,variant),size),
                        (container(stream,size+1,variant),size+1),
                        (dcx[:40]+b'KRAK'+dcx[44:],size),
                        (dcx[:72]+struct.pack('>I',7)+dcx[76:],size),
                    ):
                        with self.assertRaises(ValueError):
                            unpack(data,max_output=limit)
                        bad += 1
                    if size:
                        for data in (dcx,container(stream,size-1,variant)):
                            with self.assertRaises(ValueError):
                                unpack(data,max_output=size-1)
                            bad += 1
            print(f'{good} Go stream matches, {bad} refused cases')


if __name__ == '__main__':
    unittest.main()
