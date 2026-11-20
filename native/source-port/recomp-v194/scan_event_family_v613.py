#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline exact constructor-shape comparison, excluding the base getter target."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from ps4_ctor_order_v567 import inspect
from scan_class_family_v601 import signature


def scan(blob):
    order, _ = inspect(blob)
    rx = blob[0x4000:0x4000+0x2bbe4a8]
    with TemporaryDirectory(prefix='bb-event-shape-') as tmp:
        text = Path(tmp) / 'text'
        text.write_bytes(rx)
        ref = signature(text, order[97], 0x5bf, 0x379)[0]
        for n, start in enumerate(order, 1):
            if rx[start+0x3be:start+0x3c1] != b'\x48\x8d\x05':
                continue
            shape, getter = signature(text, start, 0x5bf, 0x379)
            if shape == ref:
                yield n, start, getter


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decrypted_elf', type=Path)
    args = parser.parse_args()
    for n, start, getter in scan(args.decrypted_elf.read_bytes()):
        print(n, hex(start), hex(getter), sep='\t')
