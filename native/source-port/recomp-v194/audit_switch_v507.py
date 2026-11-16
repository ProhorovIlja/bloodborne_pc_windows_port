# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline comparison of an RX switch against an independent analyst export."""
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct

from switch_scan_v506 import recover


def compare(image, digest, rx, evidence):
    if (type(evidence) is not dict or set(evidence) != {'image_sha256', 'switches'}
            or evidence['image_sha256'] != digest or type(evidence['switches']) is not list
            or not 1 <= len(evidence['switches']) <= 4096):
        raise ValueError('invalid or mismatched switch evidence')
    _, _, offset, base, _, size, _, _ = rx
    if not 0 < size <= 128 << 20 or not 0 <= offset <= len(image)-size:
        raise ValueError('invalid RX extent')
    segment = image[offset:offset+size]
    seen = set()
    summary = {'checked': 0, 'matched': 0, 'rejected': 0, 'mismatched': 0,
               'runtime_verified': False}
    for row in evidence['switches']:
        if type(row) is not dict or set(row) != {'entry', 'table', 'default', 'targets'}:
            raise ValueError('invalid switch record')
        entry, table, default, targets = (row[k] for k in ('entry', 'table', 'default', 'targets'))
        if type(targets) is not list or not 1 <= len(targets) <= 128 or any(
                type(a) is not int or not base <= a < base+size for a in (entry, table, default, *targets)):
            raise ValueError('invalid switch addresses')
        if entry in seen:
            raise ValueError('duplicate entry')
        seen.add(entry)
        summary['checked'] += 1
        try:
            result = recover(segment, base, entry, {default, *targets})
        except ValueError:
            summary['rejected'] += 1
        else:
            key = 'matched' if result == (table, default, tuple(targets)) else 'mismatched'
            summary[key] += 1
    return summary


def main():
    from census_v480 import census
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf', required=True, type=Path)
    p.add_argument('--first-load-slot', required=True, type=lambda s: int(s, 0))
    p.add_argument('--evidence', required=True, type=Path)
    args = p.parse_args()
    try:
        if any(x.is_symlink() or not x.is_file() or not 0 < x.stat().st_size <= limit
               for x, limit in ((args.elf, 512 << 20), (args.evidence, 16 << 20))):
            raise ValueError('invalid input file')
        evidence = json.loads(args.evidence.read_text(encoding='utf-8'))
        with args.elf.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as im:
            digest = hashlib.sha256(im).hexdigest()
            if type(evidence) is not dict or evidence.get('image_sha256') != digest:
                raise ValueError('ELF hash does not match evidence')
            layout = {}
            census(im, args.first_load_slot, evidence=layout)
            report = compare(im, digest, layout['rx'], evidence)
    except (OSError, ValueError, KeyError, struct.error, RecursionError):
        p.exit(2, 'V507 refused: invalid input, ELF metadata or evidence\n')
    print(json.dumps(report, sort_keys=True))
    return 0 if report['matched'] == report['checked'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
